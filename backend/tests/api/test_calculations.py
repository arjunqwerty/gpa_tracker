"""Phase 3: course analysis, simulation, GPA / CGPA (predicted vs confirmed), target CGPA and credits."""
from tests.api.helpers import THEORY, add_history, create_course, create_semester, ok

GRADE_FOR_POINT = {10: "S", 9: "A", 8: "B", 7: "C", 6: "D", 5: "E"}
# Semester 4 of the workbook: (credits, grade point) per course -> 205 / 23.5
WORKBOOK_SEMESTER_4 = [(4, 9), (3, 8), (2, 8), (1, 10), (1.5, 8), (3, 9), (1, 9), (3, 8), (1, 10), (3, 9), (1, 10)]


def test_course_calculation(client):
    course = create_course(client, create_semester(client)["id"], assessments=THEORY)
    analysis = ok(client.get(f"/api/courses/{course['id']}/calculation"))
    assert analysis["current_marks"] == 51.6
    assert analysis["maximum_possible_marks"] == 91.6
    assert analysis["projected_marks"] == 86
    assert (analysis["predicted_grade"], analysis["predicted_grade_point"]) == ("A", 9)
    assert analysis["pending_assessments"] == ["FAT"]
    targets = {t["grade"]: t for t in analysis["targets"]}
    assert list(targets) == ["S", "A", "B", "C", "D", "E"]
    assert targets["S"]["required_marks"] == {"FAT": 96}
    assert targets["E"]["status"] == "already_achieved"


def test_simulation_does_not_save_anything(client):
    course = create_course(client, create_semester(client)["id"], assessments=THEORY)
    fat = course["assessments"][-1]
    analysis = ok(client.post(f"/api/courses/{course['id']}/simulate", json={"marks": {fat["id"]: 64}}))
    assert analysis["current_marks"] == 77.2 and analysis["predicted_grade"] == "B"
    assert ok(client.get(f"/api/courses/{course['id']}"))["assessments"][-1]["obtained_marks"] is None
    assert client.post(f"/api/courses/{course['id']}/simulate", json={"marks": {fat["id"]: 101}}).status_code == 422


def test_rounding_setting_changes_prediction(client):
    almost_s = [{"name": "Exam", "maximum_marks": 100, "weightage": 100, "obtained_marks": 89.5, "status": "completed"}]
    course = create_course(client, create_semester(client)["id"], assessments=almost_s)
    assert ok(client.get(f"/api/courses/{course['id']}/calculation"))["predicted_grade"] == "A"
    profile = ok(client.get("/api/profile"))
    profile["settings"]["round_marks_before_grading"] = True
    ok(client.put("/api/profile", json=profile))
    assert ok(client.get(f"/api/courses/{course['id']}/calculation"))["predicted_grade"] == "S"


def test_semester_gpa_matches_workbook_semester_4(client):
    semester = create_semester(client, 4)
    for i, (credits, point) in enumerate(WORKBOOK_SEMESTER_4):
        add_history(client, semester["id"], f"C{i}", GRADE_FOR_POINT[point], credits=credits)
    report = ok(client.get(f"/api/semesters/{semester['id']}/gpa"))
    assert report["confirmed"]["gpa_credits"] == 23.5
    assert report["confirmed"]["grade_points"] == 205
    assert round(report["confirmed"]["gpa"], 6) == round(205 / 23.5, 6)
    assert report["predicted"] == report["confirmed"]


def test_predicted_and_confirmed_gpa_stay_separate(client):
    semester = create_semester(client)
    add_history(client, semester["id"], "DONE", "S", credits=3)
    create_course(client, semester["id"], code="TRACKED", credits=3, assessments=THEORY)  # predicted A
    provisional = create_course(client, semester["id"], code="DECLARED", credits=2)
    ok(client.put(f"/api/courses/{provisional['id']}/official-result", json={"grade": "B"}))
    create_course(client, semester["id"], code="NO_MARKS", credits=4)  # nothing known yet

    report = ok(client.get(f"/api/semesters/{semester['id']}/gpa"))
    assert report["confirmed"]["gpa"] == 10
    assert report["predicted"]["gpa_credits"] == 8  # 3 confirmed + 3 predicted + 2 provisional
    assert report["predicted"]["grade_points"] == 30 + 27 + 16
    assert {c["course_code"]: c["basis"] for c in report["courses"]} == {
        "DONE": "confirmed", "TRACKED": "predicted", "DECLARED": "provisional", "NO_MARKS": None}


def test_cgpa_progression_and_non_gpa_courses(client):
    first, second = create_semester(client, 1), create_semester(client, 2)
    add_history(client, first["id"], "A1", "S", credits=4)
    add_history(client, first["id"], "NGCR", "P", credits=2, counts_towards_gpa=False, category="NGCR")
    add_history(client, second["id"], "B1", "B", credits=4)

    report = ok(client.get("/api/cgpa"))
    assert report["confirmed"]["gpa_credits"] == 8
    assert report["confirmed"]["cgpa"] == 9
    assert [s["confirmed_cgpa"] for s in report["semesters"]] == [10, 9]
    assert [s["confirmed_gpa"] for s in report["semesters"]] == [10, 8]


def test_repeated_course_replaces_earlier_attempt_in_cgpa(client):
    first, second = create_semester(client, 1), create_semester(client, 2)
    add_history(client, first["id"], "BMAT101L", "F", credits=4)
    add_history(client, second["id"], "BMAT101L", "A", credits=4, attempt=2)
    assert ok(client.get("/api/cgpa"))["confirmed"]["cgpa"] == 9


def test_target_cgpa(client):
    semester = create_semester(client)
    add_history(client, semester["id"], "X", "A", credits=10)  # CGPA 9 over 10 credits
    target = ok(client.post("/api/cgpa/target", json={"target_cgpa": 9.5, "remaining_credits": 10}))
    assert (target["status"], target["required_gpa"]) == ("achievable", 10)
    assert ok(client.post("/api/cgpa/target", json={"target_cgpa": 9.6, "remaining_credits": 10}))["status"] == "not_achievable"
    assert ok(client.post("/api/cgpa/target", json={"target_cgpa": 9, "remaining_credits": 0}))["status"] == "already_achieved"
    # Without remaining_credits, the curriculum's remaining credits are used (161 - 10).
    default = ok(client.post("/api/cgpa/target", json={"target_cgpa": 9.5}))
    assert round(default["required_gpa"], 6) == round((9.5 * 161 - 90) / 151, 6)


def test_credit_progress(client):
    semester = create_semester(client)
    for i, credits in enumerate([3, 3, 4]):  # 10 credits against an Open Elective requirement of 9
        add_history(client, semester["id"], f"OE{i}", "A", credits=credits, category="OE")
    add_history(client, semester["id"], "NG", "P", credits=2, counts_towards_gpa=False, category="NGCR")
    add_history(client, semester["id"], "FAIL", "F", credits=3, category="DC")  # failed: not earned
    create_course(client, semester["id"], code="NO_CAT", credits=3)  # missing category
    create_course(client, semester["id"], code="ODD", credits=3, category_code="XYZ")
    create_course(client, semester["id"], code="DONE?", credits=3, category_code="DC", status="completed")

    report = ok(client.get("/api/credits/progress"))
    assert (report["required_credits"], report["earned_credits"], report["remaining_credits"]) == (161, 12, 149)
    assert (report["gpa_credits"], report["non_gpa_credits"]) == (10, 2)
    oe = next(c for c in report["categories"] if c["code"] == "OE")
    assert (oe["earned_credits"], oe["remaining_credits"], oe["surplus_credits"]) == (10, 0, 1)
    assert report["semesters"][0]["registered_credits"] == 24
    assert report["semesters"][0]["earned_credits"] == 12
    warnings = {(w["type"], w["course_code"]) for w in report["warnings"]}
    assert {("missing_category", "NO_CAT"), ("unknown_category", "ODD"), ("missing_official_grade", "DONE?")} <= warnings


def test_withdrawn_courses_are_ignored(client):
    semester = create_semester(client)
    create_course(client, semester["id"], code="W", credits=3, status="withdrawn", assessments=THEORY)
    assert ok(client.get(f"/api/semesters/{semester['id']}/gpa"))["courses"] == []
