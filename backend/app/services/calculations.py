"""Runs the calculation engine over a user's stored academic record.

The engine reads plain attributes, so assessments, grade entries and official
results are passed in as they are stored. Nothing calculated here is saved:
GPA, CGPA and credit totals are always derived from the records on request.

"Confirmed" figures use confirmed official results only. "Predicted" figures
use the best grade known for each course: its official result (confirmed or
provisional), otherwise the grade predicted from its marks.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal

from app.engine import credits as credit_engine
from app.engine import gpa as gpa_engine
from app.engine import marks as marks_engine
from app.models import Course, CurriculumVersion, GradingScheme, Semester, User
from app.ownership import visible_to


@dataclass
class CourseGrade:
    course_id: str
    course_code: str
    title: str
    credits: Decimal
    counts_towards_gpa: bool
    grade: str | None
    grade_point: Decimal | None
    basis: str | None  # confirmed | provisional | predicted | None (nothing known yet)


@dataclass
class SemesterGpa:
    semester_id: str
    label: str
    confirmed: gpa_engine.GpaSummary
    predicted: gpa_engine.GpaSummary
    courses: list[CourseGrade]


@dataclass
class AcademicRecord:
    semesters: list[Semester]  # in chronological order
    courses: list[Course]  # withdrawn courses left out unless asked for
    schemes: dict  # grading scheme id -> GradingScheme (every version)


async def load_schemes(user: User) -> dict:
    return {s.id: s for s in await GradingScheme.find(GradingScheme.user_id == user.id).to_list()}


async def load_record(user: User, include_withdrawn: bool = False) -> AcademicRecord:
    semesters = sorted(await Semester.find(Semester.user_id == user.id).to_list(), key=lambda s: s.sort_key)
    query = {"user_id": user.id} if include_withdrawn else {"user_id": user.id, "status": {"$ne": "withdrawn"}}
    courses = await Course.find(query).sort("course_code").to_list()
    return AcademicRecord(semesters, courses, await load_schemes(user))


# --- Courses ---

def analyse_course(course: Course, schemes: dict, user: User, assessments=None) -> marks_engine.CourseAnalysis:
    """`assessments` overrides the stored ones (used for "what if" simulations)."""
    scheme = schemes.get(course.grading_scheme_id)
    return marks_engine.analyse_course(
        course.assessments if assessments is None else assessments,
        scheme.entries if scheme else [],
        round_marks=user.settings.round_marks_before_grading,
    )


def course_grade(course: Course, schemes: dict, user: User) -> CourseGrade:
    result = course.official_result
    if result:
        grade, grade_point, basis = result.grade, result.grade_point, result.result_status
        credits, counts_towards_gpa = result.credits, result.counts_towards_gpa
    else:
        analysis = analyse_course(course, schemes, user)
        grade, grade_point = analysis.predicted_grade, analysis.predicted_grade_point
        basis = "predicted" if grade else None
        credits, counts_towards_gpa = course.credits, course.counts_towards_gpa
    return CourseGrade(str(course.id), course.course_code, course.title, credits, counts_towards_gpa, grade, grade_point, basis)


# --- GPA and CGPA ---

def summarise_semester(semester: Semester, courses: list[Course], schemes: dict, user: User) -> SemesterGpa:
    grades = [course_grade(c, schemes, user) for c in courses if c.semester_id == semester.id]
    return SemesterGpa(
        semester_id=str(semester.id),
        label=semester.label,
        confirmed=gpa_engine.calculate_semester_gpa([g for g in grades if g.basis == "confirmed"]),
        predicted=gpa_engine.calculate_semester_gpa([g for g in grades if g.grade_point is not None]),
        courses=grades,
    )


def latest_attempts_only(courses: list[Course]) -> list[Course]:
    """A repeated course replaces its earlier graded attempts in the CGPA (outstanding decision 7)."""
    latest = defaultdict(int)
    for course in courses:
        if course.official_result:
            latest[course.course_code] = max(latest[course.course_code], course.attempt)
    return [c for c in courses if not c.official_result or c.attempt == latest[c.course_code]]


def cgpa_report(record: AcademicRecord, user: User) -> dict:
    courses = latest_attempts_only(record.courses)
    semesters = [summarise_semester(s, courses, record.schemes, user) for s in record.semesters]
    confirmed = gpa_engine.calculate_cumulative_cgpa([s.confirmed for s in semesters])
    predicted = gpa_engine.calculate_cumulative_cgpa([s.predicted for s in semesters])
    return {
        "confirmed": confirmed,
        "predicted": predicted,
        "semesters": [
            {
                "semester_id": s.semester_id,
                "label": s.label,
                "confirmed_gpa": s.confirmed.gpa,
                "predicted_gpa": s.predicted.gpa,
                "confirmed_cgpa": confirmed.progression[i],
                "predicted_cgpa": predicted.progression[i],
                "gpa_credits": s.confirmed.gpa_credits,
            }
            for i, s in enumerate(semesters)
        ],
    }


# --- Credits ---

def _credit_view(course: Course) -> credit_engine.CreditCourse:
    result = course.official_result
    return credit_engine.CreditCourse(
        credits=result.credits if result else course.credits,
        category_code=result.category_code if result else course.category_code,
        is_earned=course.is_confirmed and result.is_passing and course.counts_towards_earned_credits,
        counts_towards_requirement=course.counts_towards_requirement,
    )


async def user_curriculum(user: User) -> CurriculumVersion | None:
    if not user.profile.curriculum_version_id:
        return None
    return await CurriculumVersion.find_one({"_id": user.profile.curriculum_version_id, **visible_to(user)})


def credit_report(record: AcademicRecord, curriculum: CurriculumVersion | None) -> dict:
    views = {course.id: _credit_view(course) for course in record.courses}
    earned_courses = [c for c in record.courses if views[c.id].is_earned]
    categories = curriculum.categories if curriculum else []
    category_codes = {c.code for c in categories}

    required = curriculum.total_required_credits if curriculum else Decimal(0)
    earned = credit_engine.calculate_earned_credits(views.values())
    gpa_credits = sum((views[c.id].credits for c in earned_courses if c.official_result.counts_towards_gpa), Decimal(0))
    difference = credit_engine.calculate_remaining_credits(required, earned)

    return {
        "curriculum": {"id": str(curriculum.id), "version_name": curriculum.version_name} if curriculum else None,
        "required_credits": required,
        "earned_credits": earned,
        "remaining_credits": max(difference, Decimal(0)),
        "surplus_credits": max(-difference, Decimal(0)),
        "completion_percentage": credit_engine.calculate_credit_completion_percentage(required, earned),
        "gpa_credits": gpa_credits,
        "non_gpa_credits": earned - gpa_credits,
        "categories": credit_engine.calculate_category_progress(views.values(), categories),
        "uncategorised_credits": sum(
            (views[c.id].credits for c in earned_courses if views[c.id].category_code not in category_codes), Decimal(0)
        ),
        "semesters": [
            {
                "semester_id": str(s.id),
                "label": s.label,
                "registered_credits": sum((views[c.id].credits for c in record.courses if c.semester_id == s.id), Decimal(0)),
                "earned_credits": sum((views[c.id].credits for c in earned_courses if c.semester_id == s.id), Decimal(0)),
            }
            for s in record.semesters
        ],
        "warnings": credit_warnings(record.courses, views, category_codes),
    }


def credit_warnings(courses: list[Course], views: dict, category_codes: set[str]) -> list[dict]:
    """Problems that would make the credit totals misleading (spec FR-10.5)."""
    warnings = []

    def warn(kind, course, message):
        warnings.append({"type": kind, "course_id": str(course.id), "course_code": course.course_code, "message": message})

    categories_by_code = defaultdict(set)
    for course in courses:
        view = views[course.id]
        if course.counts_towards_requirement and not view.category_code:
            warn("missing_category", course, "Has no curriculum category, so its credits count towards no requirement. Edit the course to choose one.")
        elif view.category_code and category_codes and view.category_code not in category_codes:
            warn("unknown_category", course, f"Its category {view.category_code} is not in your curriculum, so its credits count towards no requirement. Edit the course to choose a listed category.")
        if course.status in ("completed", "failed") and not course.is_confirmed:
            warn("missing_official_grade", course, "Is marked completed but has no confirmed result, so its credits are not earned yet. Record and confirm the grade on the course page.")
        if view.is_earned and view.category_code:
            categories_by_code[course.course_code].add(view.category_code)

    for course in courses:
        if len(categories_by_code.get(course.course_code, ())) > 1 and views[course.id].is_earned:
            warn("conflicting_categories", course, f"Is counted in more than one category. Give every attempt of {course.course_code} the same category.")
    return warnings


def target_cgpa(record: AcademicRecord, user: User, target: Decimal, remaining_credits: Decimal) -> gpa_engine.TargetCgpa:
    confirmed = cgpa_report(record, user)["confirmed"]
    default_scheme = record.schemes.get(user.settings.default_grading_scheme_id)
    max_point = max((e.grade_point for e in default_scheme.entries), default=Decimal(10)) if default_scheme else Decimal(10)
    return gpa_engine.calculate_target_cgpa(target, confirmed.grade_points, confirmed.gpa_credits, remaining_credits, max_point)


# --- Analytics ---

def grade_distribution(record: AcademicRecord, user: User) -> dict:
    """How many confirmed grades of each kind: overall, per curriculum category and per course type."""
    results = [(course, course.official_result) for course in record.courses if course.is_confirmed]
    scheme = record.schemes.get(user.settings.default_grading_scheme_id)
    scheme_order = [entry.grade for entry in scheme.entries] if scheme else []
    grades = scheme_order + sorted({result.grade for _, result in results} - set(scheme_order))

    by_category, by_course_type = defaultdict(Counter), defaultdict(Counter)
    for course, result in results:
        by_category[result.category_code or "none"][result.grade] += 1
        by_course_type[course.course_type_code or "none"][result.grade] += 1
    return {
        "grades": grades,
        "overall": Counter(result.grade for _, result in results),
        "by_category": by_category,
        "by_course_type": by_course_type,
    }
