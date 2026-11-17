"""Phase 2: seed data, profile, curricula, course types and grading schemes."""
from tests.api.helpers import THEORY, create_course, create_semester, ok


def test_new_account_starts_with_vit_data(client, db):
    assert db.users.count_documents({}) == 1
    curriculum = ok(client.get("/api/curricula"))[0]
    assert len(curriculum["categories"]) == 10
    assert sum(c["required_credits"] for c in curriculum["categories"]) == 161
    assert len(curriculum["course_templates"]) == 65
    assert {"TH", "LO", "SS", "ETL", "OC", "ECA", "PJT"} <= {t["code"] for t in ok(client.get("/api/course-types"))}

    profile = ok(client.get("/api/profile"))
    assert profile["profile"]["curriculum_version_id"] == curriculum["id"]
    scheme = ok(client.get("/api/grading-schemes"))[0]
    assert profile["settings"]["default_grading_scheme_id"] == scheme["id"]
    assert [e["grade"] for e in scheme["entries"]] == ["S", "A", "B", "C", "D", "E", "F", "P", "N"]


def test_seeding_twice_creates_nothing_new(client, db):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app):  # second start-up
        pass
    assert db.users.count_documents({}) == 1
    assert db.curriculum_versions.count_documents({}) == 1
    assert db.grading_schemes.count_documents({}) == 1


def test_update_profile(client):
    data = ok(client.get("/api/profile"))
    data["profile"]["full_name"] = "Arjun"
    data["settings"]["target_cgpa"] = 9
    ok(client.put("/api/profile", json=data))
    saved = ok(client.get("/api/profile"))
    assert saved["profile"]["full_name"] == "Arjun"
    assert saved["settings"]["target_cgpa"] == 9


def test_profile_rejects_unknown_references(client):
    data = ok(client.get("/api/profile"))
    data["settings"]["default_grading_scheme_id"] = "6afa0dde8cfc9c26b5b81bc3"
    assert client.put("/api/profile", json=data).status_code == 404


def test_shared_curriculum_is_read_only_but_can_be_copied(client):
    shared = ok(client.get("/api/curricula"))[0]
    shared["categories"][0]["required_credits"] = 30
    assert client.put(f"/api/curricula/{shared['id']}", json=shared).status_code == 404

    copy = ok(client.post(f"/api/curricula/{shared['id']}/copy"), 201)
    assert copy["user_id"] is not None and copy["version_name"] == "2021 (my copy)"
    copy["categories"][0]["required_credits"] = 30
    updated = ok(client.put(f"/api/curricula/{copy['id']}", json=copy))
    assert updated["categories"][0]["required_credits"] == 30
    assert ok(client.get(f"/api/curricula/{shared['id']}"))["categories"][0]["required_credits"] == 24


def test_create_course_type(client):
    ok(client.post("/api/course-types", json={"code": "NPTEL", "name": "NPTEL online course"}), 201)
    assert "NPTEL" in [t["code"] for t in ok(client.get("/api/course-types"))]


def test_programmes(client):
    university = ok(client.get("/api/universities"))[0]
    ok(client.post("/api/programmes", json={"university_id": university["id"], "name": "B.Tech IT",
                                            "degree_type": "B.Tech", "duration_semesters": 8}), 201)
    assert len(ok(client.get("/api/programmes"))) == 2


def test_grading_scheme_rejects_duplicate_grades(client):
    entries = [{"grade": "S", "grade_point": 10, "minimum_marks": 90}, {"grade": "S", "grade_point": 9, "minimum_marks": 80}]
    assert client.post("/api/grading-schemes", json={"name": "Bad", "entries": entries}).status_code == 422


def test_editing_a_grading_scheme_creates_a_new_version(client):
    old = ok(client.get("/api/grading-schemes"))[0]
    semester = create_semester(client)
    course = create_course(client, semester["id"], assessments=THEORY)
    assert course["grading_scheme_id"] == old["id"]

    old["entries"][4]["minimum_marks"] = 56  # move the D boundary
    new = ok(client.put(f"/api/grading-schemes/{old['id']}", json={"name": old["name"], "entries": old["entries"]}))
    assert new["version"] == 2 and new["scheme_key"] == old["scheme_key"]

    assert [s["id"] for s in ok(client.get("/api/grading-schemes"))] == [new["id"]]
    archived = ok(client.get("/api/grading-schemes?include_archived=true"))
    assert {s["version"] for s in archived} == {1, 2}
    assert ok(client.get(f"/api/courses/{course['id']}"))["grading_scheme_id"] == new["id"]  # in-progress course moved
    assert ok(client.get("/api/profile"))["settings"]["default_grading_scheme_id"] == new["id"]
    assert client.put(f"/api/grading-schemes/{old['id']}", json={"name": "x", "entries": old["entries"]}).status_code == 409
