"""Phase 3: official results (provisional -> confirmed), snapshots, audit log and grade history."""
from tests.api.helpers import THEORY, add_history, create_course, create_semester, ok


def test_result_lifecycle_is_audited(client, db):
    semester = create_semester(client)
    course = create_course(client, semester["id"], assessments=THEORY, category_code="DC")

    course = ok(client.put(f"/api/courses/{course['id']}/official-result", json={"grade": "A", "source": "generated"}))
    result = course["official_result"]
    assert (result["grade"], result["grade_point"], result["result_status"]) == ("A", 9, "provisional")
    assert (result["credits"], result["category_code"], result["grading_scheme_version"]) == (3, "DC", 1)
    assert course["status"] == "in_progress"

    course = ok(client.post(f"/api/courses/{course['id']}/official-result/confirm"))
    assert course["official_result"]["result_status"] == "confirmed"
    assert course["official_result"]["confirmed_at"] is not None
    assert course["status"] == "completed"
    assert [a["action"] for a in db.audit_log.find().sort("created_at")] == ["set_result", "confirm_result"]


def test_failing_grade_marks_course_failed(client):
    semester = create_semester(client)
    course = create_course(client, semester["id"])
    ok(client.put(f"/api/courses/{course['id']}/official-result", json={"grade": "F"}))
    assert ok(client.post(f"/api/courses/{course['id']}/official-result/confirm"))["status"] == "failed"


def test_grade_must_exist_in_the_scheme(client):
    semester = create_semester(client)
    course = create_course(client, semester["id"])
    response = client.put(f"/api/courses/{course['id']}/official-result", json={"grade": "Z"})
    assert response.status_code == 422 and "not part of the grading scheme" in response.text


def test_confirm_without_result_is_rejected(client):
    course = create_course(client, create_semester(client)["id"])
    assert client.post(f"/api/courses/{course['id']}/official-result/confirm").status_code == 404


def test_confirmed_results_are_protected(client):
    semester = create_semester(client)
    course = create_course(client, semester["id"])
    ok(client.put(f"/api/courses/{course['id']}/official-result", json={"grade": "B"}))
    ok(client.post(f"/api/courses/{course['id']}/official-result/confirm"))
    assert client.delete(f"/api/courses/{course['id']}").status_code == 409
    assert client.delete(f"/api/courses/{course['id']}/official-result").status_code == 409
    assert client.delete(f"/api/semesters/{semester['id']}").status_code == 409


def test_provisional_result_can_be_removed(client):
    course = create_course(client, create_semester(client)["id"])
    ok(client.put(f"/api/courses/{course['id']}/official-result", json={"grade": "B"}))
    assert ok(client.delete(f"/api/courses/{course['id']}/official-result"))["official_result"] is None


def test_result_snapshot_survives_course_and_scheme_edits(client):
    semester = create_semester(client)
    course = create_course(client, semester["id"], credits=3, category_code="DC")
    ok(client.put(f"/api/courses/{course['id']}/official-result", json={"grade": "A"}))
    ok(client.post(f"/api/courses/{course['id']}/official-result/confirm"))

    ok(client.put(f"/api/courses/{course['id']}", json={"semester_id": semester["id"], "course_code": course["course_code"],
                                                       "title": "Renamed", "credits": 10, "category_code": "OE"}))
    scheme = ok(client.get("/api/grading-schemes"))[0]
    scheme["entries"][1]["grade_point"] = 8  # change what an A is worth
    ok(client.put(f"/api/grading-schemes/{scheme['id']}", json={"name": scheme["name"], "entries": scheme["entries"]}))

    result = ok(client.get(f"/api/courses/{course['id']}"))["official_result"]
    assert (result["credits"], result["category_code"], result["grade_point"], result["grading_scheme_version"]) == (3, "DC", 9, 1)
    assert ok(client.get("/api/cgpa"))["confirmed"]["cgpa"] == 9


def test_manual_history_entries(client, db):
    semester = create_semester(client, 1)
    entry = add_history(client, semester["id"], "BMAT101L", "A", credits=3, category="FCBSM", exam_month="2022-01-01T00:00:00Z")
    assert entry["source"] == "manual" and entry["assessments"] == [] and entry["status"] == "completed"
    assert entry["official_result"]["result_status"] == "confirmed"
    assert db.audit_log.count_documents({"action": "create"}) == 1


def test_history_cannot_contain_the_same_course_twice(client):
    semester = create_semester(client)
    add_history(client, semester["id"], "BMAT101L", "A")
    duplicate = {"semester_id": semester["id"], "course_code": "BMAT101L", "title": "Again", "credits": 3, "grade": "S"}
    assert client.post("/api/grade-history", json=duplicate).status_code == 409
    add_history(client, semester["id"], "BMAT101L", "S", attempt=2)  # a repeat is a new attempt


def test_history_filters_search_and_pagination(client):
    first, second = create_semester(client, 1), create_semester(client, 2)
    add_history(client, first["id"], "BMAT101L", "A", category="FCBSM", course_type_code="TH")
    add_history(client, first["id"], "BPHY101P", "S", credits=1, category="FCBSM", course_type_code="LO")
    add_history(client, second["id"], "BCSE202L", "S", category="DC", course_type_code="TH")
    create_course(client, second["id"], code="BCSE303L")  # in progress: not history

    def codes(query=""):
        return [c["course_code"] for c in ok(client.get(f"/api/grade-history{query}"))["items"]]

    assert len(codes()) == 3
    assert codes(f"?semester_id={first['id']}") == ["BMAT101L", "BPHY101P"]
    assert codes("?grade=S") == ["BCSE202L", "BPHY101P"]
    assert codes("?course_type=LO") == ["BPHY101P"]
    assert codes("?category=DC") == ["BCSE202L"]
    assert codes("?search=bmat") == ["BMAT101L"]
    assert codes("?search=(") == []  # regex characters are escaped
    page = ok(client.get("/api/grade-history?page=2&page_size=2"))
    assert page["total"] == 3 and len(page["items"]) == 1


def test_update_and_delete_history_entries(client, db):
    semester = create_semester(client)
    entry = add_history(client, semester["id"], "BMAT101L", "A")
    body = {"semester_id": semester["id"], "course_code": "BMAT101L", "title": "Calculus", "credits": 4, "grade": "S"}
    updated = ok(client.put(f"/api/grade-history/{entry['id']}", json=body))
    assert (updated["title"], updated["official_result"]["grade"], updated["official_result"]["credits"]) == ("Calculus", "S", 4)

    ok(client.delete(f"/api/grade-history/{entry['id']}"), 204)
    assert db.courses.count_documents({}) == 0  # typed-in entry is removed completely

    tracked = create_course(client, semester["id"], code="BCSE202L", assessments=THEORY)
    ok(client.put(f"/api/courses/{tracked['id']}/official-result", json={"grade": "B"}))
    ok(client.post(f"/api/courses/{tracked['id']}/official-result/confirm"))
    ok(client.delete(f"/api/grade-history/{tracked['id']}"), 204)
    kept = ok(client.get(f"/api/courses/{tracked['id']}"))  # tracked course keeps its marks
    assert kept["official_result"] is None and len(kept["assessments"]) == 6
