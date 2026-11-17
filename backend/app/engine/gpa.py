"""Grade points, semester GPA, CGPA and target CGPA (spec FR-07 to FR-09).

Functions accept any object with the attributes of `GradedCourse`.
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class GradedCourse:
    credits: Decimal
    grade_point: Decimal
    counts_towards_gpa: bool = True


@dataclass(frozen=True)
class GpaSummary:
    total_credits: Decimal  # every course passed in, GPA-eligible or not
    gpa_credits: Decimal
    grade_points: Decimal
    gpa: Decimal | None  # None when there are no GPA credits


@dataclass(frozen=True)
class CgpaSummary:
    gpa_credits: Decimal
    grade_points: Decimal
    cgpa: Decimal | None
    progression: list[Decimal | None]  # CGPA after each semester, in order


@dataclass(frozen=True)
class TargetCgpa:
    target_cgpa: Decimal
    required_gpa: Decimal | None  # average GPA needed over the remaining credits
    status: str  # already_achieved | achievable | not_achievable
    remaining_credits: Decimal
    highest_reachable_cgpa: Decimal | None  # with the top grade in every remaining credit


def calculate_course_grade_points(credits: Decimal, grade_point: Decimal) -> Decimal:
    return credits * grade_point


def calculate_semester_gpa(courses) -> GpaSummary:
    gpa_courses = [c for c in courses if c.counts_towards_gpa]
    gpa_credits = sum((c.credits for c in gpa_courses), Decimal(0))
    grade_points = sum((calculate_course_grade_points(c.credits, c.grade_point) for c in gpa_courses), Decimal(0))
    return GpaSummary(
        total_credits=sum((c.credits for c in courses), Decimal(0)),
        gpa_credits=gpa_credits,
        grade_points=grade_points,
        gpa=grade_points / gpa_credits if gpa_credits else None,
    )


def calculate_cumulative_cgpa(semesters: list[GpaSummary]) -> CgpaSummary:
    """CGPA is credit weighted: total grade points / total GPA credits."""
    credits = points = Decimal(0)
    progression = []
    for semester in semesters:
        credits += semester.gpa_credits
        points += semester.grade_points
        progression.append(points / credits if credits else None)
    return CgpaSummary(credits, points, progression[-1] if progression else None, progression)


def calculate_target_cgpa(
    target_cgpa: Decimal,
    earned_grade_points: Decimal,
    earned_credits: Decimal,
    remaining_credits: Decimal,
    max_grade_point: Decimal = Decimal(10),
) -> TargetCgpa:
    """Required future GPA = (target x all credits - existing grade points) / remaining credits."""
    all_credits = earned_credits + remaining_credits
    highest = (earned_grade_points + remaining_credits * max_grade_point) / all_credits if all_credits > 0 else None
    if remaining_credits <= 0:
        current = earned_grade_points / earned_credits if earned_credits else None
        reached = current is not None and current >= target_cgpa
        return TargetCgpa(target_cgpa, None, "already_achieved" if reached else "not_achievable", remaining_credits, highest)

    required = (target_cgpa * all_credits - earned_grade_points) / remaining_credits
    if required <= 0:
        status = "already_achieved"
    elif required > max_grade_point:
        status = "not_achievable"
    else:
        status = "achievable"
    return TargetCgpa(target_cgpa, required, status, remaining_credits, highest)
