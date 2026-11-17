"""Excel import in two steps.

`preview()` reads a workbook and validates every row without saving anything.
`commit()` saves a validated preview in a single transaction.

Recognised sheets (any subset; sheet names and headers are case-insensitive):

  Semesters      Number | Type | Label | Academic year | Status
  Courses        Semester | Code | Title | Course type | Credits | Category | Counts towards GPA |
                 Counts towards earned credits | Counts towards requirement | Status | Attempt |
                 Grade | Exam month | Result date
  Assessments    Semester | Course code | Name | Maximum marks | Weightage | Obtained marks | Status
  Grade history  VTOP's own layout: Course Code | Course Title | Course Type | Credits | Grade |
                 Exam Month | Result Declared | Course Distribution  (+ an optional Semester column)
  Requirements   Code | Category | Required credits

Courses refer to semesters by label. Grade-history rows without a Semester are
grouped into one semester per exam month. A grade becomes a confirmed result.
Assessments may also add marks to a course that already exists.
"""
from datetime import datetime
from io import BytesIO
from typing import Annotated, Any

import openpyxl
from beanie import PydanticObjectId
from pydantic import BaseModel, BeforeValidator, ValidationError

from app.database import transaction
from app.models import Course, CurriculumVersion, GradingScheme, ImportJob, Semester, User
from app.models.common import utc_now
from app.models.configuration import CreditCategory
from app.models.course import AssessmentFields, CourseAssessment, CourseFields, OfficialResult
from app.models.semester import SemesterFields
from app.services.calculations import user_curriculum

# Sheet -> {column header: field name}. The export writes these same headers.
SHEET_COLUMNS = {
    "Semesters": {"Number": "semester_number", "Type": "semester_type", "Label": "label",
                  "Academic year": "academic_year", "Status": "status"},
    "Courses": {"Semester": "semester", "Code": "course_code", "Title": "title", "Course type": "course_type_code",
                "Credits": "credits", "Category": "category_code", "Counts towards GPA": "counts_towards_gpa",
                "Counts towards earned credits": "counts_towards_earned_credits",
                "Counts towards requirement": "counts_towards_requirement", "Status": "status", "Attempt": "attempt",
                "Grade": "grade", "Exam month": "exam_month", "Result date": "result_date"},
    "Assessments": {"Semester": "semester", "Course code": "course_code", "Name": "name", "Maximum marks": "maximum_marks",
                    "Weightage": "weightage", "Obtained marks": "obtained_marks", "Status": "status"},
    "Grade history": {"Semester": "semester", "Course Code": "course_code", "Course Title": "title",
                      "Course Type": "course_type_code", "Credits": "credits", "Grade": "grade", "Exam Month": "exam_month",
                      "Result Declared": "result_date", "Course Distribution": "category_code"},
    "Requirements": {"Code": "code", "Category": "name", "Required credits": "required_credits"},
}


def parse_date(value):
    """Excel dates, "2024-05", "2024-05-10", "May-2024" or "May 2024"."""
    if not isinstance(value, str):
        return value
    for pattern in ("%Y-%m", "%Y-%m-%d", "%b-%Y", "%b %Y", "%B %Y"):
        try:
            return datetime.strptime(value.strip(), pattern)
        except ValueError:
            pass
    return value  # let validation report it


ExcelDate = Annotated[datetime | None, BeforeValidator(parse_date)]


class CourseRow(CourseFields):
    semester_id: PydanticObjectId | None = None  # resolved from `semester` on commit
    semester: str  # semester label
    counts_towards_gpa: bool | None = None  # None = decided by the grade (P/N-style grades do not count)
    grade: str | None = None
    exam_month: ExcelDate = None
    result_date: ExcelDate = None
    assessments: list[AssessmentFields] = []


class AssessmentRow(AssessmentFields):
    semester: str
    course_code: str


class Preview(BaseModel):
    """Everything an import will create. Stored on the ImportJob as JSON."""
    semesters: list[SemesterFields] = []
    courses: list[CourseRow] = []
    marks_for_existing_courses: dict[str, list[AssessmentFields]] = {}  # course id -> assessments
    requirements: list[CreditCategory] = []


def _read_rows(sheet, columns: dict[str, str]) -> list[tuple[int, dict]]:
    """(row number, {field: value}) for every non-empty row; unknown columns are ignored."""
    lookup = {header.lower(): field for header, field in columns.items()}
    rows = sheet.iter_rows(values_only=True)
    fields = [lookup.get(str(h).strip().lower()) if h is not None else None for h in next(rows, ())]
    result = []
    for number, values in enumerate(rows, start=2):
        row = {}
        for field, value in zip(fields, values):
            if isinstance(value, str):
                value = value.strip() or None
            if field and value is not None:
                row[field] = value
        if row:
            result.append((number, row))
    return result


def _validated(model, sheet_name: str, rows, errors: list[str]) -> list:
    valid = []
    for number, row in rows:
        try:
            valid.append(model.model_validate(row))
        except ValidationError as error:
            problems = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'row'}: {e['msg']}" for e in error.errors())
            errors.append(f"{sheet_name} row {number}: {problems}")
    return valid


def _semesters_from_exam_months(rows: list[tuple[int, dict]]) -> list[SemesterFields]:
    """VTOP grade history has no semester column. Rows without one are grouped by
    exam month (oldest first): this fills in each row's `semester` and returns the
    semesters to create."""
    unassigned = [row for _, row in rows if "semester" not in row]
    dates = (parse_date(row.get("exam_month")) for row in unassigned)
    months = sorted({d for d in dates if isinstance(d, datetime)})
    labels = {month: f"Exams {month:%b %Y}" for month in months}
    for row in unassigned:
        row["semester"] = labels.get(parse_date(row.get("exam_month")), "Imported results")
    semesters = [SemesterFields(semester_number=i + 1, label=labels[m], status="completed") for i, m in enumerate(months)]
    if any(row["semester"] == "Imported results" for row in unassigned):
        semesters.append(SemesterFields(semester_number=len(semesters) + 1, label="Imported results", status="completed"))
    return semesters


async def preview(user: User, filename: str, content: bytes) -> ImportJob:
    errors, warnings = [], []
    found = Preview()
    try:
        workbook = openpyxl.load_workbook(BytesIO(content), data_only=True, read_only=True)
    except Exception:
        workbook = None
        errors.append("The file could not be opened as an Excel (.xlsx) workbook.")

    if workbook:
        sheets = {ws.title.strip().lower(): ws for ws in workbook.worksheets}
        known = {name.lower(): name for name in SHEET_COLUMNS}
        warnings += [f"Sheet '{ws.title}' was ignored (not a recognised sheet)." for key, ws in sheets.items() if key not in known]

        def rows_of(name):
            sheet = sheets.get(name.lower())
            return _read_rows(sheet, SHEET_COLUMNS[name]) if sheet else []

        # VTOP's sheet has subtotal rows (credits only) between semesters: skip rows without a course code.
        history_rows = [(number, row) for number, row in rows_of("Grade history") if "course_code" in row]
        inferred = _semesters_from_exam_months(history_rows)
        if inferred:
            warnings.append("Grade history has no Semester column, so one semester was created per exam month. "
                            "Rename them or move courses afterwards if needed.")

        semesters = _validated(SemesterFields, "Semesters", rows_of("Semesters"), errors) + inferred
        courses = _validated(CourseRow, "Courses", rows_of("Courses"), errors)
        courses += _validated(CourseRow, "Grade history", history_rows, errors)
        assessments = _validated(AssessmentRow, "Assessments", rows_of("Assessments"), errors)
        found.requirements = _validated(CreditCategory, "Requirements", rows_of("Requirements"), errors)
        await _check_against_database(user, found, semesters, courses, assessments, errors, warnings)

    nothing_found = not (found.semesters or found.courses or found.marks_for_existing_courses or found.requirements)
    if workbook and not errors and nothing_found:
        errors.append("Nothing to import was found.")
    return await ImportJob(
        user_id=user.id, filename=filename, status="failed" if errors else "validated",
        preview=found.model_dump(mode="json"), errors=errors, warnings=warnings,
    ).insert()


async def _check_against_database(user, found: Preview, semesters, courses, assessments, errors, warnings):
    """Cross-row checks: semesters exist, no duplicates, grades exist in the grading scheme."""
    existing_semesters = {s.label: s for s in await Semester.find(Semester.user_id == user.id).to_list()}
    existing_courses = await Course.find(Course.user_id == user.id).to_list()
    semester_label = {s.id: s.label for s in existing_semesters.values()}
    existing_keys = {(semester_label.get(c.semester_id), c.course_code, c.attempt): c for c in existing_courses}
    graded_keys = {(c.course_code, c.attempt) for c in existing_courses if c.official_result}
    scheme = await GradingScheme.get(user.settings.default_grading_scheme_id)

    for semester in semesters:
        if semester.label in existing_semesters:
            warnings.append(f"Semester '{semester.label}' already exists and will be reused.")
        elif semester.label not in {s.label for s in found.semesters}:
            found.semesters.append(semester)
    known_labels = set(existing_semesters) | {s.label for s in found.semesters}

    imported = {}
    for course in courses:
        key = (course.semester, course.course_code, course.attempt)
        where = f"{course.course_code} ({course.semester})"
        if course.semester not in known_labels:
            errors.append(f"{where}: semester '{course.semester}' is not in the Semesters sheet or your semesters.")
        elif key in imported or key in existing_keys:
            errors.append(f"{where}: this course appears twice (in the file or already in your record).")
        elif course.grade and (course.course_code, course.attempt) in graded_keys:
            errors.append(f"{where}: already has an official result for attempt {course.attempt}.")
        elif course.grade and not (scheme and scheme.entry_for(course.grade)):
            errors.append(f"{where}: grade '{course.grade}' is not in your grading scheme.")
        else:
            if course.counts_towards_gpa is None:
                entry = scheme.entry_for(course.grade) if course.grade else None
                course.counts_towards_gpa = entry is None or entry.minimum_marks is not None
            imported[key] = course
    found.courses = list(imported.values())

    imported_by_course = {(label, code): c for (label, code, _), c in imported.items()}
    existing_by_course = {(label, code): c for (label, code, _), c in existing_keys.items()}
    for row in assessments:
        assessment = AssessmentFields(**row.model_dump(exclude={"semester", "course_code"}))
        course = imported_by_course.get((row.semester, row.course_code))
        existing = existing_by_course.get((row.semester, row.course_code))
        if course:
            course.assessments.append(assessment)
        elif existing:
            found.marks_for_existing_courses.setdefault(str(existing.id), []).append(assessment)
        else:
            errors.append(f"Assessment '{row.name}': course {row.course_code} in '{row.semester}' was not found.")


async def commit(job: ImportJob, user: User):
    found = Preview.model_validate(job.preview)
    scheme = await GradingScheme.get(user.settings.default_grading_scheme_id)
    async with transaction() as session:
        semester_ids = {s.label: s.id for s in await Semester.find(Semester.user_id == user.id, session=session).to_list()}
        for fields in found.semesters:
            semester = await Semester(user_id=user.id, **fields.model_dump()).insert(session=session)
            semester_ids[semester.label] = semester.id

        for row in found.courses:
            course = Course(
                user_id=user.id, source="import", **{**row.model_dump(include=set(CourseFields.model_fields)),
                "semester_id": semester_ids[row.semester], "grading_scheme_id": scheme.id},
                assessments=[a.model_dump() for a in row.assessments],
            )
            if row.grade:
                course.official_result = OfficialResult.snapshot(
                    course, scheme, row.grade, result_status="provisional", source="import",
                    exam_month=row.exam_month, result_date=row.result_date)
                course.confirm_result()
            await course.insert(session=session)

        for course_id, assessments in found.marks_for_existing_courses.items():
            course = await Course.find_one({"_id": PydanticObjectId(course_id), "user_id": user.id}, session=session)
            by_name = {a.name: i for i, a in enumerate(course.assessments)}
            for assessment in assessments:  # same name = update its marks, otherwise add it
                if assessment.name in by_name:
                    old = course.assessments[by_name[assessment.name]]
                    course.assessments[by_name[assessment.name]] = CourseAssessment(id=old.id, **assessment.model_dump())
                else:
                    course.assessments.append(CourseAssessment(**assessment.model_dump()))
            await course.save(session=session)

        if found.requirements:
            await _replace_requirements(user, found.requirements, session)

        job.status, job.committed_at, job.expires_at = "committed", utc_now(), None
        await job.save(session=session)


async def _replace_requirements(user: User, categories: list[CreditCategory], session):
    """Requirements go into the user's own curriculum (a shared one is copied first)."""
    curriculum = await user_curriculum(user)
    if curriculum is None or curriculum.user_id is None:
        base: dict[str, Any] = curriculum.model_dump(include={"programme_id", "effective_year", "course_templates"}) if curriculum else {}
        name = f"{curriculum.version_name} (imported)" if curriculum else "Imported curriculum"
        curriculum = CurriculumVersion(user_id=user.id, version_name=name, **base)
    curriculum.categories = categories
    await curriculum.save(session=session)
    user.profile.curriculum_version_id = curriculum.id
    await user.save(session=session)
