"""Curriculum credit progress (spec FR-10).

`courses` are objects with the attributes of `CreditCourse`;
`requirements` are objects with `code`, `name` and `required_credits`
(the curriculum's categories).
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CreditCourse:
    credits: Decimal
    category_code: str | None
    is_earned: bool  # passed, and counts towards earned credits
    counts_towards_requirement: bool = True


@dataclass(frozen=True)
class CategoryProgress:
    code: str
    name: str
    required_credits: Decimal
    earned_credits: Decimal
    remaining_credits: Decimal  # never negative...
    surplus_credits: Decimal  # ...anything above the requirement shows up here
    completion_percentage: Decimal | None


def calculate_earned_credits(courses) -> Decimal:
    return sum((c.credits for c in courses if c.is_earned), Decimal(0))


def calculate_remaining_credits(required: Decimal, earned: Decimal) -> Decimal:
    """Negative when more credits were earned than required."""
    return required - earned


def calculate_credit_completion_percentage(required: Decimal, earned: Decimal) -> Decimal | None:
    return earned / required * 100 if required else None


def calculate_category_progress(courses, requirements) -> list[CategoryProgress]:
    progress = []
    for requirement in requirements:
        earned = calculate_earned_credits(
            c for c in courses if c.counts_towards_requirement and c.category_code == requirement.code
        )
        difference = calculate_remaining_credits(requirement.required_credits, earned)
        progress.append(CategoryProgress(
            code=requirement.code,
            name=requirement.name,
            required_credits=requirement.required_credits,
            earned_credits=earned,
            remaining_credits=max(difference, Decimal(0)),
            surplus_credits=max(-difference, Decimal(0)),
            completion_percentage=calculate_credit_completion_percentage(requirement.required_credits, earned),
        ))
    return progress
