"""Building downloadable files: Excel, CSV and PDF.

The Excel workbook uses exactly the import's sheet layout (see excel_import.SHEET_COLUMNS),
so an exported workbook can be imported again.
"""
import csv
from datetime import datetime
from decimal import Decimal
from io import BytesIO, StringIO

import openpyxl
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import Course, CurriculumVersion, Semester
from app.services.excel_import import SHEET_COLUMNS


def _cell(value):
    """Python value -> spreadsheet-friendly value."""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return value


def _rows(sheet: str, records: list[dict]) -> tuple[list[str], list[list]]:
    columns = SHEET_COLUMNS[sheet]
    return list(columns), [[_cell(record.get(field)) for field in columns.values()] for record in records]


def _course_record(course: Course, semester_label: str) -> dict:
    """A course as one spreadsheet row; only confirmed grades are exported."""
    record = {**course.model_dump(), "semester": semester_label}
    if course.is_confirmed:
        result = course.official_result
        record.update(grade=result.grade, category_code=result.category_code, credits=result.credits,
                      exam_month=result.exam_month.strftime("%Y-%m") if result.exam_month else None,
                      result_date=result.result_date)
    return record


def workbook(semesters: list[Semester], courses: list[Course], curriculum: CurriculumVersion | None) -> bytes:
    """Everything in the import layout. With no data it is the blank import template."""
    labels = {s.id: s.label for s in semesters}
    assessments = [
        {**a.model_dump(), "semester": labels[c.semester_id], "course_code": c.course_code}
        for c in courses for a in c.assessments
    ]
    return xlsx({
        "Semesters": _rows("Semesters", [s.model_dump() for s in semesters]),
        "Courses": _rows("Courses", [_course_record(c, labels[c.semester_id]) for c in courses]),
        "Assessments": _rows("Assessments", assessments),
        "Requirements": _rows("Requirements", [c.model_dump() for c in curriculum.categories] if curriculum else []),
    })


def grade_history_rows(semesters: list[Semester], courses: list[Course]) -> tuple[list[str], list[list]]:
    """Confirmed results in VTOP's grade-history layout (plus the semester)."""
    labels = {s.id: s.label for s in semesters}
    graded = [c for c in courses if c.is_confirmed]
    return _rows("Grade history", [_course_record(c, labels[c.semester_id]) for c in graded])


def xlsx(sheets: dict[str, tuple[list[str], list[list]]]) -> bytes:
    book = openpyxl.Workbook()
    book.remove(book.active)
    for name, (headers, rows) in sheets.items():
        sheet = book.create_sheet(name)
        sheet.append(headers)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for row in rows:
            sheet.append(row)
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def csv_bytes(headers: list[str], rows: list[list]) -> bytes:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def credit_rows(credits: dict) -> tuple[list[str], list[list]]:
    """The credit report (from calculations.credit_report) as a table."""
    headers = ["Code", "Category", "Required", "Earned", "Remaining", "Surplus", "Completion %"]
    rows = [
        [c.code, c.name, _cell(c.required_credits), _cell(c.earned_credits), _cell(c.remaining_credits),
         _cell(c.surplus_credits), None if c.completion_percentage is None else round(float(c.completion_percentage), 1)]
        for c in credits["categories"]
    ]
    rows.append(["", "Total", _cell(credits["required_credits"]), _cell(credits["earned_credits"]),
                 _cell(credits["remaining_credits"]), _cell(credits["surplus_credits"]), None])
    return headers, rows


# --- PDF ---

def _number(value, digits=2) -> str:
    return "-" if value is None else f"{float(value):.{digits}f}".rstrip("0").rstrip(".")


def _table(rows: list[list], column_widths: list[int] | None = None) -> Table:
    table = Table(rows, colWidths=column_widths, hAlign="LEFT", repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f5")]),
    ]))
    return table


def summary_pdf(name: str, cgpa: dict, semesters: list, credits: dict | None) -> bytes:
    """`semesters` are SemesterGpa results; pass one for a semester report, all for the full summary.
    `credits` (the credit report) adds the curriculum section."""
    styles = getSampleStyleSheet()
    story = [Paragraph(f"Academic summary - {name}", styles["Title"]),
             Paragraph(f"Generated {datetime.now():%d %b %Y}", styles["Normal"]), Spacer(1, 12)]

    confirmed, predicted = cgpa["confirmed"], cgpa["predicted"]
    story.append(_table([
        ["CGPA (confirmed)", "CGPA (predicted)", "GPA credits"],
        [_number(confirmed.cgpa), _number(predicted.cgpa), _number(confirmed.gpa_credits)],
    ]))

    for semester in semesters:
        story += [Spacer(1, 14), Paragraph(
            f"{semester.label} - GPA {_number(semester.confirmed.gpa)} (predicted {_number(semester.predicted.gpa)})",
            styles["Heading3"])]
        rows = [["Code", "Title", "Credits", "Grade", "Grade point", "Basis"]]
        rows += [[g.course_code, Paragraph(g.title, styles["Normal"]), _number(g.credits), g.grade or "-",
                  _number(g.grade_point) if g.counts_towards_gpa else "non-GPA", g.basis or "-"] for g in semester.courses]
        story.append(_table(rows, column_widths=[70, 220, 50, 40, 70, 70]))

    if credits:
        story += [Spacer(1, 14), Paragraph("Credits by curriculum category", styles["Heading3"])]
        headers, rows = credit_rows(credits)
        story.append(_table([headers] + [[_number(v) if isinstance(v, float) else v for v in row] for row in rows]))

    output = BytesIO()
    SimpleDocTemplate(output, pagesize=A4, title="Academic summary").build(story)
    return output.getvalue()
