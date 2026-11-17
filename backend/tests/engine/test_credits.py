"""Credit progress, checked against the workbook's "Credit split" sheet."""
from decimal import Decimal as D
from types import SimpleNamespace

from app.engine.credits import (
    CreditCourse,
    calculate_category_progress,
    calculate_credit_completion_percentage,
    calculate_earned_credits,
    calculate_remaining_credits,
)

REQUIREMENTS = [
    SimpleNamespace(code="OE", name="Open Elective", required_credits=D(9)),
    SimpleNamespace(code="DC", name="Discipline Core", required_credits=D(44)),
]


def test_earned_credits_only_count_earned_courses():
    courses = [CreditCourse(D(3), "DC", True), CreditCourse(D(4), "DC", False), CreditCourse(D(2), "NGCR", True)]
    assert calculate_earned_credits(courses) == 5


def test_remaining_and_completion():
    assert calculate_remaining_credits(D(161), D(162)) == -1  # surplus is not hidden
    assert calculate_credit_completion_percentage(D(44), D(11)) == 25
    assert calculate_credit_completion_percentage(D(0), D(0)) is None  # e.g. Bridge Course


def test_category_progress_shows_surplus():
    # Open Elective: 10 earned against 9 required in the workbook.
    courses = [CreditCourse(D("3.5"), "OE", True), CreditCourse(D("3.5"), "OE", True), CreditCourse(D(3), "OE", True),
               CreditCourse(D(3), "DC", True), CreditCourse(D(3), "DC", True, counts_towards_requirement=False)]
    oe, dc = calculate_category_progress(courses, REQUIREMENTS)
    assert (oe.earned_credits, oe.remaining_credits, oe.surplus_credits) == (10, 0, 1)
    assert (dc.earned_credits, dc.remaining_credits, dc.surplus_credits) == (3, 41, 0)
