"""Phase 6: one user can never read or change another user's data, through any endpoint.

Every route is tried by user B against user A's documents. A route added later is picked up
automatically; if it takes a request body, add one to BODIES below.
"""
import re

from app.main import app
from tests.api.helpers import THEORY, add_history, create_course, create_semester, login, ok, register

USER_OWNED = ["users", "semesters", "courses", "grading_schemes", "curriculum_versions", "course_types",
              "import_jobs", "audit_log"]


def build_user_a(client) -> dict:
    """User A with one of every kind of document. Returns A's ids by path-parameter name."""
    register(client, "a@example.com", name="Alice Secret")
    semester = create_semester(client)
    course = create_course(client, semester["id"], assessments=THEORY)
    history = add_history(client, semester["id"], "BCSE101L", "A")
    scheme = ok(client.get("/api/grading-schemes"))[0]
    shared = ok(client.get("/api/curricula"))[0]
    curriculum = ok(client.post(f"/api/curricula/{shared['id']}/copy"), 201)
    ok(client.post("/api/course-types", json={"code": "XX", "name": "Alice's type"}), 201)
    template = client.get("/api/import/template.xlsx").content
    job = ok(client.post("/api/import", files={"file": ("a.xlsx", template)}), 201)
    return {
        "semester_id": semester["id"], "course_id": course["id"], "assessment_id": course["assessments"][0]["id"],
        "history_id": history["id"], "scheme_id": scheme["id"], "curriculum_id": curriculum["id"], "job_id": job["id"],
        "semester": semester, "course": course, "scheme": scheme, "curriculum": curriculum,
    }


def bodies(a: dict) -> dict:
    """Valid request bodies, so a request fails on ownership rather than on validation."""
    return {
        ("PUT", "/api/semesters/{semester_id}"): a["semester"],
        ("PUT", "/api/courses/{course_id}"): a["course"],
        ("POST", "/api/courses/{course_id}/duplicate"): {},
        ("POST", "/api/courses/{course_id}/assessments"): THEORY[0],
        ("PUT", "/api/courses/{course_id}/assessments/{assessment_id}"): THEORY[0],
        ("PUT", "/api/courses/{course_id}/official-result"): {"grade": "A"},
        ("POST", "/api/courses/{course_id}/simulate"): {"marks": {}},
        ("PUT", "/api/grade-history/{course_id}"): {**a["course"], "grade": "S"},
        ("PUT", "/api/grading-schemes/{scheme_id}"): a["scheme"],
        ("PUT", "/api/curricula/{curriculum_id}"): a["curriculum"],
    }


def stored_data(db, user_id) -> dict:
    return {name: list(db[name].find({"user_id" if name != "users" else "_id": user_id})) for name in USER_OWNED}


def test_user_b_cannot_touch_user_a(anonymous, db):
    a = build_user_a(anonymous)
    a_user_id = db.users.find_one({"email": "a@example.com"})["_id"]
    a_before = stored_data(db, a_user_id)
    secrets = [a[key] for key in a if key.endswith("_id")] + [str(a_user_id), "Alice Secret", "a@example.com"]

    register(anonymous, "b@example.com")
    request_bodies = bodies(a)
    routes = [(method.upper(), path) for path, methods in app.openapi()["paths"].items() for method in methods
              if not path.startswith("/api/auth")]
    assert len(routes) > 50
    for method, route in routes:
        path = re.sub(r"\{(\w+)\}", lambda m: a[m.group(1)], route)
        response = anonymous.request(method, path, json=request_bodies.get((method, route)))
        if "{" in route:
            assert response.status_code == 404, f"{method} {route}: {response.status_code} {response.text}"
        leaked = [secret for secret in secrets if secret in response.text]
        assert not leaked, f"{method} {route} shows user A's data: {leaked}"

    # B may not attach B's own records to A's semester, curriculum or grading scheme.
    attempts = [
        ("/api/courses", {"semester_id": a["semester_id"], "course_code": "X1", "title": "X", "credits": 3}),
        ("/api/courses", {"semester_id": create_semester(anonymous)["id"], "course_code": "X1", "title": "X",
                          "credits": 3, "grading_scheme_id": a["scheme_id"]}),
        ("/api/grade-history", {"semester_id": a["semester_id"], "course_code": "X1", "title": "X", "credits": 3, "grade": "A"}),
        ("/api/courses/from-template", {"semester_id": a["semester_id"], "curriculum_version_id": a["curriculum_id"],
                                        "template_ids": []}),
    ]
    for path, body in attempts:
        assert anonymous.post(path, json=body).status_code == 404, path
    profile = ok(anonymous.get("/api/profile"))
    profile["profile"]["curriculum_version_id"] = a["curriculum_id"]
    assert anonymous.put("/api/profile", json=profile).status_code == 404

    assert stored_data(db, a_user_id) == a_before
    login(anonymous, "a@example.com")
    assert len(ok(anonymous.get("/api/courses"))) == 2
