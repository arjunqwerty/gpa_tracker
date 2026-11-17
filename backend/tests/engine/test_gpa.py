"""GPA / CGPA calculations, checked against the reference workbook (marks.xlsx)."""
from decimal import Decimal as D

import pytest

from app.engine.gpa import (
    GpaSummary,
    GradedCourse,
    calculate_cumulative_cgpa,
    calculate_semester_gpa,
    calculate_target_cgpa,
)


# (credits, grade point) per course, and the totals, from the "Semester N" sheets.
WORKBOOK_SEMESTERS = {
    4: ([(4, 9), (3, 8), (2, 8), (1, 10), (1.5, 8), (3, 9), (1, 9), (3, 8), (1, 10), (3, 9), (1, 10)], "23.5", "205"),
    5: ([(3, 8), (1, 9), (3, 10), (3, 9), (1, 10), (1.5, 10), (3, 9), (1, 10), (1, 6), (1, 6)], "18.5", "164"),
    6: ([(1, 8), (1, 8), (3, 8), (1, 10), (3, 8), (1, 8), (3, 8), (3, 5), (2, 8), (1, 9), (1.5, 9), (1, 10)], "21.5", "169.5"),
    7: ([(2, 8), (1, 9), (3, 9), (1, 10), (3, 9), (2, 8), (1, 9), (2, 8), (1, 10), (2, 9), (1, 10), (3, 10), (3, 8)], "25", "222"),
}


@pytest.mark.parametrize("semester", WORKBOOK_SEMESTERS)
def test_semester_gpa_matches_workbook(semester):
    courses, credits, grade_points = WORKBOOK_SEMESTERS[semester]
    summary = calculate_semester_gpa([GradedCourse(D(str(c)), D(p)) for c, p in courses])
    assert summary.gpa_credits == D(credits)
    assert summary.grade_points == D(grade_points)
    assert summary.gpa == D(grade_points) / D(credits)


def test_non_gpa_courses_are_excluded():
    summary = calculate_semester_gpa([GradedCourse(D(3), D(9)), GradedCourse(D(2), D(0), counts_towards_gpa=False)])
    assert summary.total_credits == 5
    assert summary.gpa_credits == 3
    assert summary.gpa == 9


def test_semester_without_gpa_credits_has_no_gpa():
    assert calculate_semester_gpa([]).gpa is None


def test_cgpa_sheet_progression():
    semesters = [(D("9.5"), D("16.5")), (D("8.95"), D("19.5")), (D("208.5") / D("22.5"), D("22.5")), (D("8.6"), D("23.5")),
                 (D(164) / D("18.5"), D("18.5")), (D("169.5") / D("21.5"), D("21.5")), (D("8.88"), D(25)), (D(9), D(5))]
    summaries = [GpaSummary(credits, credits, gpa * credits, gpa) for gpa, credits in semesters]
    result = calculate_cumulative_cgpa(summaries)
    assert result.gpa_credits == 152
    assert round(result.grade_points, 6) == D("1342.375")
    assert round(result.cgpa, 10) == D("8.8314144737")
    assert round(result.progression[1], 10) == D("9.2020833333")  # after semester 2
    assert len(result.progression) == 8


def test_target_cgpa_matches_workbook_formula():
    # CGPA sheet: ((9 x 146) - 1111.495) / (146 - 123)
    result = calculate_target_cgpa(D(9), D("1111.495"), D(123), D(23))
    assert result.status == "achievable"
    assert round(result.required_gpa, 10) == D("8.8045652174")
    assert calculate_target_cgpa(D(10), D("1111.495"), D(123), D(23)).status == "not_achievable"
    assert calculate_target_cgpa(D(5), D("1111.495"), D(123), D(23)).status == "already_achieved"


def test_target_cgpa_without_remaining_credits_does_not_divide_by_zero():
    # The workbook shows #DIV/0! here.
    assert calculate_target_cgpa(D(8), D(900), D(100), D(0)).status == "already_achieved"
    assert calculate_target_cgpa(D(9.5), D(900), D(100), D(0)).status == "not_achievable"


def test_target_cgpa_reports_the_highest_reachable_cgpa():
    result = calculate_target_cgpa(D(10), D(900), D(100), D(20))
    assert result.status == "not_achievable"
    assert result.highest_reachable_cgpa == D(1100) / D(120)
    assert result.remaining_credits == D(20)
