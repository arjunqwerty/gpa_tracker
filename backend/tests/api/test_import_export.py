"""Phase 5: grade analytics, Excel import (preview -> commit) and exports."""
import csv
import io
import json

import openpyxl

from tests.api.helpers import THEORY, add_history, create_course, create_semester, ok


def workbook(**sheets) -> bytes:
    """workbook(Courses=[headers, row, ...]) -> .xlsx bytes. Underscores in sheet names become spaces."""
    book = openpyxl.Workbook()
    book.remove(book.active)
    for name, rows in sheets.items():
        sheet = book.create_sheet(name.replace("_", " "))
        for row in rows:
            sheet.append(row)
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


def upload(client, content: bytes, status=201):
    files = {"file": ("record.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    return ok(client.post("/api/import", files=files), status)


def read_xlsx(content: bytes) -> dict[str, list[tuple]]:
    book = openpyxl.load_workbook(io.BytesIO(content))
    return {sheet.title: list(sheet.iter_rows(values_only=True)) for sheet in book.worksheets}


# --- Analytics ---

def test_grade_distribution(client):
    semester = create_semester(client)
    add_history(client, semester["id"], "A1", "S", category="DC", course_type_code="TH")
    add_history(client, semester["id"], "A2", "S", category="DC", course_type_code="LO")
    add_history(client, semester["id"], "A3", "A", category="OE", course_type_code="TH")
    create_course(client, semester["id"], code="TRACKED", assessments=THEORY)  # predicted only: not counted

    report = ok(client.get("/api/dashboard/grade-distribution"))
    assert report["grades"][:3] == ["S", "A", "B"]  # in the grading scheme's order
    assert report["overall"] == {"S": 2, "A": 1}
    assert report["by_category"] == {"DC": {"S": 2}, "OE": {"A": 1}}
    assert report["by_course_type"] == {"TH": {"S": 1, "A": 1}, "LO": {"S": 1}}


# --- Import ---

def test_template_has_every_sheet(client):
    sheets = read_xlsx(client.get("/api/import/template.xlsx").content)
    assert list(sheets) == ["Semesters", "Courses", "Assessments", "Requirements"]
    assert sheets["Assessments"][0][:3] == ("Semester", "Course code", "Name")


def test_import_preview_then_commit(client, db):
    content = workbook(
        Semesters=[["Number", "Label", "Status"], [4, "Semester 4", "completed"], [5, "Semester 5", "active"]],
        Courses=[
            ["Semester", "Code", "Title", "Course type", "Credits", "Category", "Grade", "Exam month"],
            ["Semester 4", "BMAT201L", "Complex Variables", "TH", 4, "FCBSM", "A", "2023-04"],
            ["Semester 5", "BCSE302L", "Database Systems", "TH", 3, "DC", None, None],
        ],
        Assessments=[
            ["Semester", "Course code", "Name", "Maximum marks", "Weightage", "Obtained marks", "Status"],
            ["Semester 5", "BCSE302L", "CAT 1", 50, 15, 36, "completed"],
            ["Semester 5", "BCSE302L", "FAT", 100, 85, None, "pending"],
        ],
        Requirements=[["Code", "Category", "Required credits"], ["DC", "Discipline Core", 50], ["FCBSM", "Maths", 24]],
    )
    job = upload(client, content)
    assert job["status"] == "validated" and job["errors"] == []
    assert len(job["preview"]["semesters"]) == 2 and len(job["preview"]["courses"]) == 2
    assert db.courses.count_documents({}) == 0  # nothing saved yet
    assert job["expires_at"] is not None

    job = ok(client.post(f"/api/import/{job['id']}/commit"))
    assert job["status"] == "committed" and job["expires_at"] is None

    courses = {c["course_code"]: c for c in ok(client.get("/api/courses"))}
    graded, tracked = courses["BMAT201L"], courses["BCSE302L"]
    assert graded["official_result"]["result_status"] == "confirmed" and graded["official_result"]["source"] == "import"
    assert graded["official_result"]["exam_month"].startswith("2023-04")
    assert [a["name"] for a in tracked["assessments"]] == ["CAT 1", "FAT"]
    assert ok(client.get("/api/cgpa"))["confirmed"]["cgpa"] == 9

    credits = ok(client.get("/api/credits/progress"))
    assert credits["required_credits"] == 74  # requirements replaced (in a copy of the shared curriculum)
    assert credits["curriculum"]["version_name"] == "2021 (imported)"
    assert client.post(f"/api/import/{job['id']}/commit").status_code == 409  # only once


def test_vtop_grade_history_sheet(client):
    """The sheet as copied from VTOP: no semester column, subtotal rows, P grades."""
    headers = ["Sl.No.", "Course Code", "Course Title", "Course Type", "Credits", "Grade", "Exam Month", "Result Declared", "Course Distribution"]
    content = workbook(Grade_history=[
        headers,
        [1, "BCSE101E", "Computer Programming: Python", "ETL", 3, "S", "2022-01", "2022-02-22", "FCBES"],
        [2, "BCSE101N", "Introduction to Engineering", "PJT", 1, "P", "2022-01", "2022-02-22", "NGCR"],
        [3, "BMAT101L", "Calculus", "TH", 3, "A", "2022-01", "2022-02-22", "FCBSM"],
        [None, None, None, None, 7],  # subtotal row: ignored
        [4, "BCHY101L", "Engineering Chemistry", "TH", 3, "B", "Jun-2022", "2022-07-25", "FCBSM"],
    ])
    job = upload(client, content)
    assert job["status"] == "validated", job["errors"]
    assert [s["label"] for s in job["preview"]["semesters"]] == ["Exams Jan 2022", "Exams Jun 2022"]
    assert any("one semester was created per exam month" in w for w in job["warnings"])
    ok(client.post(f"/api/import/{job['id']}/commit"))

    pass_course = next(c for c in ok(client.get("/api/courses")) if c["course_code"] == "BCSE101N")
    assert pass_course["counts_towards_gpa"] is False  # P is never predicted from marks -> non-GPA
    report = ok(client.get("/api/cgpa"))
    assert [s["confirmed_gpa"] for s in report["semesters"]] == [9.5, 8]  # (30 + 27) / 6, then B
    assert ok(client.get("/api/credits/progress"))["earned_credits"] == 10


def test_invalid_rows_block_the_commit(client, db):
    create_semester(client, 1, label="Semester 1")
    add_history(client, ok(client.get("/api/semesters"))[0]["id"], "BMAT101L", "A")
    content = workbook(Courses=[
        ["Semester", "Code", "Title", "Credits", "Grade"],
        ["Semester 9", "X1", "Unknown semester", 3, None],
        ["Semester 1", "BMAT101L", "Already graded", 3, "S"],
        ["Semester 1", "X2", "Bad grade", 3, "Z"],
        ["Semester 1", "X3", "Bad credits", "lots", None],
        ["Semester 1", "X4", "Twice", 3, None],
        ["Semester 1", "X4", "Twice", 3, None],
    ])
    job = upload(client, content)
    assert job["status"] == "failed"
    messages = " | ".join(job["errors"])
    for expected in ["semester 'Semester 9'", "appears twice", "grade 'Z'", "Courses row 5: credits"]:
        assert expected in messages
    assert client.post(f"/api/import/{job['id']}/commit").status_code == 409
    assert db.courses.count_documents({}) == 1


def test_not_an_excel_file(client):
    job = upload(client, b"definitely not a spreadsheet")
    assert job["status"] == "failed" and "could not be opened" in job["errors"][0]


def test_marks_for_an_existing_course_are_updated(client):
    semester = create_semester(client, 5, label="Semester 5")
    course = create_course(client, semester["id"], code="BCSE302L", assessments=THEORY)
    content = workbook(Assessments=[
        ["Semester", "Course code", "Name", "Maximum marks", "Weightage", "Obtained marks", "Status"],
        ["Semester 5", "BCSE302L", "FAT", 100, 40, 64, "completed"],  # existing: marks updated
        ["Semester 5", "BCSE302L", "Bonus quiz", 5, 0, 5, "completed"],  # new: added
    ])
    job = upload(client, content)
    ok(client.post(f"/api/import/{job['id']}/commit"))
    assessments = {a["name"]: a for a in ok(client.get(f"/api/courses/{course['id']}"))["assessments"]}
    assert assessments["FAT"]["obtained_marks"] == 64 and assessments["FAT"]["id"] == course["assessments"][-1]["id"]
    assert "Bonus quiz" in assessments
    assert ok(client.get(f"/api/courses/{course['id']}/calculation"))["current_marks"] == 77.2


def test_workbook_export_can_be_imported_again(client, db):
    first = create_semester(client, 1, label="Semester 1", academic_year="2021-22")
    second = create_semester(client, 2, label="Semester 2")
    add_history(client, first["id"], "BMAT101L", "A", credits=3, exam_month="2022-01-01")
    add_history(client, first["id"], "NG", "P", credits=2, counts_towards_gpa=False, category="NGCR")
    create_course(client, second["id"], code="BCSE202L", assessments=THEORY, category_code="DC")
    before = ok(client.get("/api/cgpa"))
    exported = client.get("/api/export/workbook.xlsx")
    assert exported.headers["content-disposition"] == 'attachment; filename="academic-record.xlsx"'

    db.semesters.delete_many({})
    db.courses.delete_many({})
    job = upload(client, exported.content)
    assert job["status"] == "validated", job["errors"]
    ok(client.post(f"/api/import/{job['id']}/commit"))

    assert ok(client.get("/api/cgpa"))["confirmed"] == before["confirmed"]
    tracked = next(c for c in ok(client.get("/api/courses")) if c["course_code"] == "BCSE202L")
    assert [a["obtained_marks"] for a in tracked["assessments"]] == [36, 46, 9, 9, 9, None]
    assert ok(client.get("/api/semesters"))[0]["academic_year"] == "2021-22"


# --- Exports ---

def test_grade_history_and_credit_exports(client):
    semester = create_semester(client)
    add_history(client, semester["id"], "BMAT101L", "A", credits=3, category="FCBSM", course_type_code="TH")
    rows = list(csv.reader(io.StringIO(client.get("/api/export/grade-history.csv").text)))
    assert rows[0][:4] == ["Semester", "Course Code", "Course Title", "Course Type"]
    assert rows[1][1:6] == ["BMAT101L", "Course BMAT101L", "TH", "3.0", "A"]

    sheets = read_xlsx(client.get("/api/export/grade-history.xlsx").content)
    assert sheets["Grade history"][1][1] == "BMAT101L"

    credit_rows = list(csv.reader(io.StringIO(client.get("/api/export/credits.csv").text)))
    fcbsm = next(r for r in credit_rows if r[0] == "FCBSM")
    assert fcbsm[2:4] == ["24.0", "3.0"]
    assert credit_rows[-1][1] == "Total"


def test_pdf_reports(client):
    semester = create_semester(client)
    add_history(client, semester["id"], "BMAT101L", "A")
    create_course(client, semester["id"], code="BCSE202L", assessments=THEORY)
    summary = client.get("/api/export/summary.pdf")
    assert summary.headers["content-type"] == "application/pdf" and summary.content.startswith(b"%PDF")
    report = client.get(f"/api/export/semesters/{semester['id']}.pdf")
    assert report.status_code == 200 and report.content.startswith(b"%PDF")


def test_full_json_backup(client):
    semester = create_semester(client)
    add_history(client, semester["id"], "BMAT101L", "A")
    response = client.get("/api/export/full.json")
    backup = json.loads(response.content)
    assert "attachment" in response.headers["content-disposition"]
    assert backup["courses"][0]["course_code"] == "BMAT101L" and "id" in backup["courses"][0]
    assert backup["courses"][0]["credits"] == 3
    assert len(backup["semesters"]) == 1 and len(backup["grading_schemes"]) == 1
    assert backup["audit_log"][0]["action"] == "create"
