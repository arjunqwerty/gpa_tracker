"""Phase 2: semesters, courses, templates and assessments."""
from bson import ObjectId

from tests.api.helpers import THEORY, create_course, create_semester, ok


def test_semesters_are_listed_in_order(client):
    create_semester(client, 2)
    create_semester(client, 1, label="Summer", semester_type="summer")
    create_semester(client, 1)
    labels = [s["label"] for s in ok(client.get("/api/semesters"))]
    assert labels == ["Semester 1", "Summer", "Semester 2"]


def test_update_semester(client):
    semester = create_semester(client, 1)
    updated = ok(client.put(f"/api/semesters/{semester['id']}", json={"semester_number": 1, "label": "Fall 22", "status": "completed"}))
    assert (updated["label"], updated["status"]) == ("Fall 22", "completed")


def test_create_course_with_assessments(client):
    semester = create_semester(client)
    course = create_course(client, semester["id"], assessments=THEORY)
    assert len(course["assessments"]) == 6
    assert all(a["id"] for a in course["assessments"])
    assert course["assessments"][0]["obtained_marks"] == 36
    assert len(ok(client.get(f"/api/courses?semester_id={semester['id']}"))) == 1


def test_course_needs_an_owned_semester(client):
    assert client.post("/api/courses", json={"semester_id": str(ObjectId()), "course_code": "X", "title": "X",
                                             "credits": 3}).status_code == 404


def test_validation_rules(client):
    semester = create_semester(client)
    too_many = {"name": "CAT 1", "maximum_marks": 50, "weightage": 15, "obtained_marks": 51, "status": "completed"}
    assert client.post("/api/courses", json={"semester_id": semester["id"], "course_code": "X", "title": "X",
                                             "credits": 3, "assessments": [too_many]}).status_code == 422
    assert client.post("/api/courses", json={"semester_id": semester["id"], "course_code": "X", "title": "X",
                                             "credits": -1}).status_code == 422
    course = create_course(client, semester["id"])
    zero_max = {"name": "Quiz", "maximum_marks": 0, "weightage": 10}
    assert client.post(f"/api/courses/{course['id']}/assessments", json=zero_max).status_code == 422
    allowed = {**too_many, "allow_over_max": True}  # bonus marks, explicitly allowed
    ok(client.post(f"/api/courses/{course['id']}/assessments", json=allowed), 201)


def test_courses_from_templates_copy_default_assessments(client):
    semester = create_semester(client)
    curriculum = ok(client.get("/api/curricula"))[0]
    theory = next(t for t in curriculum["course_templates"] if t["course_code"] == "BMAT101L")
    non_graded = next(t for t in curriculum["course_templates"] if t["course_code"] == "BHUM101N")

    courses = ok(client.post("/api/courses/from-template", json={
        "semester_id": semester["id"], "curriculum_version_id": curriculum["id"],
        "template_ids": [theory["template_id"], non_graded["template_id"]],
    }), 201)

    calculus, ethics = courses
    assert (calculus["course_code"], calculus["credits"], calculus["category_code"]) == ("BMAT101L", 3, "FCBSM")
    assert [a["name"] for a in calculus["assessments"]] == ["CAT 1", "CAT 2", "DA 1", "DA 2", "DA 3", "FAT"]
    assert calculus["source"] == "template" and calculus["template_id"] == theory["template_id"]
    assert ethics["counts_towards_gpa"] is False and ethics["assessments"] == []


def test_unknown_template_is_rejected(client):
    semester = create_semester(client)
    curriculum = ok(client.get("/api/curricula"))[0]
    response = client.post("/api/courses/from-template", json={
        "semester_id": semester["id"], "curriculum_version_id": curriculum["id"], "template_ids": [str(ObjectId())]})
    assert response.status_code == 404


def test_update_and_delete_course(client):
    semester, other = create_semester(client, 1), create_semester(client, 2)
    course = create_course(client, semester["id"])
    body = {k: course[k] for k in ("course_code", "title", "credits")} | {"semester_id": other["id"], "credits": 4}
    updated = ok(client.put(f"/api/courses/{course['id']}", json=body))
    assert (updated["semester_id"], updated["credits"]) == (other["id"], 4)
    ok(client.delete(f"/api/courses/{course['id']}"), 204)
    assert client.get(f"/api/courses/{course['id']}").status_code == 404


def test_duplicate_copies_structure_without_marks(client):
    semester, next_semester = create_semester(client, 1), create_semester(client, 2)
    course = create_course(client, semester["id"], assessments=THEORY)
    copy = ok(client.post(f"/api/courses/{course['id']}/duplicate", json={"semester_id": next_semester["id"]}), 201)
    assert copy["id"] != course["id"] and copy["semester_id"] == next_semester["id"]
    assert [a["name"] for a in copy["assessments"]] == [a["name"] for a in THEORY]
    assert all(a["obtained_marks"] is None and a["status"] == "pending" for a in copy["assessments"])
    assert {a["id"] for a in copy["assessments"]}.isdisjoint({a["id"] for a in course["assessments"]})


def test_assessment_crud(client):
    semester = create_semester(client)
    course = create_course(client, semester["id"])
    course = ok(client.post(f"/api/courses/{course['id']}/assessments",
                            json={"name": "FAT", "maximum_marks": 100, "weightage": 40}), 201)
    fat = course["assessments"][0]
    assert fat["status"] == "pending" and fat["obtained_marks"] is None

    course = ok(client.put(f"/api/courses/{course['id']}/assessments/{fat['id']}",
                           json={"name": "FAT", "maximum_marks": 100, "weightage": 40, "obtained_marks": 64.5, "status": "completed"}))
    assert course["assessments"][0]["obtained_marks"] == 64.5 and course["assessments"][0]["id"] == fat["id"]
    assert len(ok(client.get(f"/api/courses/{course['id']}/assessments"))) == 1

    course = ok(client.delete(f"/api/courses/{course['id']}/assessments/{fat['id']}"))
    assert course["assessments"] == []
    assert client.delete(f"/api/courses/{course['id']}/assessments/{fat['id']}").status_code == 404


def test_marks_are_stored_as_decimal128(client, db):
    semester = create_semester(client)
    create_course(client, semester["id"], credits=1.5, assessments=THEORY)
    stored = db.courses.find_one()
    assert type(stored["credits"]).__name__ == "Decimal128"
    assert type(stored["assessments"][0]["obtained_marks"]).__name__ == "Decimal128"


def test_delete_semester_removes_its_courses(client, db):
    semester = create_semester(client)
    create_course(client, semester["id"])
    ok(client.delete(f"/api/semesters/{semester['id']}"), 204)
    assert db.semesters.count_documents({}) == 0 and db.courses.count_documents({}) == 0


def test_other_users_data_is_invisible(client, db):
    """Ownership filters are in place even before login exists."""
    stranger = ObjectId()
    semester_id = db.semesters.insert_one({"user_id": stranger, "semester_number": 1, "semester_type": "regular",
                                           "label": "Theirs", "status": "active"}).inserted_id
    course_id = db.courses.insert_one({"user_id": stranger, "semester_id": semester_id, "course_code": "X",
                                       "title": "X", "credits": 3, "assessments": []}).inserted_id
    assert ok(client.get("/api/semesters")) == []
    assert ok(client.get("/api/courses")) == []
    assert client.get(f"/api/semesters/{semester_id}").status_code == 404
    assert client.get(f"/api/courses/{course_id}").status_code == 404
    assert client.delete(f"/api/courses/{course_id}").status_code == 404
    assert client.post("/api/courses", json={"semester_id": str(semester_id), "course_code": "Y", "title": "Y",
                                             "credits": 3}).status_code == 404


def test_inputs_have_sensible_limits(client):
    semester = create_semester(client)
    base = {"semester_id": semester["id"], "course_code": "BMAT101L", "title": "Calculus", "credits": 3}
    for bad in ({"title": "x" * 201}, {"credits": 500}, {"course_code": "   "}, {"attempt": 99}):
        assert client.post("/api/courses", json={**base, **bad}).status_code == 422, bad
    assert client.post("/api/semesters", json={"semester_number": 1, "label": ""}).status_code == 422
    assert client.post(f"/api/courses/{create_course(client, semester['id'])['id']}/assessments",
                       json={"name": "CAT 1", "maximum_marks": 50, "weightage": 150}).status_code == 422

    course = ok(client.post("/api/courses", json={**base, "course_code": "  BMAT102L ", "title": " Calculus II "}), 201)
    assert (course["course_code"], course["title"]) == ("BMAT102L", "Calculus II")
