"""Course-level calculations: weighted marks, predicted grade and the marks
still needed for each grade.

Functions accept any object that has the attributes of `Assessment` and
`GradeBand` below, so the API passes its stored documents straight in.

Rules (see spec FR-04 / FR-05):
- weighted marks = obtained / maximum x weightage
- pending assessments contribute nothing (they are NOT zero)
- absent assessments count as zero
- exempted assessments are dropped and their weightage is spread
  proportionally over the remaining assessments
- grades are only predicted when the weightages add up to exactly 100
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

FULL_WEIGHTAGE = Decimal(100)


@dataclass(frozen=True)
class Assessment:
    name: str
    maximum_marks: Decimal
    weightage: Decimal
    obtained_marks: Decimal | None = None
    status: str = "pending"  # pending | completed | absent | exempted


@dataclass(frozen=True)
class GradeBand:
    grade: str
    grade_point: Decimal
    minimum_marks: Decimal | None  # None = only awarded manually (e.g. P, N)
    is_passing: bool = True


@dataclass(frozen=True)
class GradeTarget:
    grade: str
    minimum_marks: Decimal
    status: str  # already_achieved | achievable | not_achievable | pending_configuration
    required_percentage: Decimal | None = None  # needed on every pending assessment
    required_marks: dict[str, Decimal] = field(default_factory=dict)  # per pending assessment


@dataclass(frozen=True)
class CourseAnalysis:
    weightage_total: Decimal
    is_configuration_complete: bool
    current_marks: Decimal
    maximum_possible_marks: Decimal
    projected_marks: Decimal | None
    predicted_grade: str | None
    predicted_grade_point: Decimal | None
    pending_assessments: list[str]
    targets: list[GradeTarget]


def calculate_assessment_weighted_marks(assessment) -> Decimal | None:
    """Contribution of one assessment, or None when it contributes nothing yet."""
    if assessment.status == "absent":
        return Decimal(0)
    if assessment.status != "completed" or assessment.obtained_marks is None:
        return None
    return assessment.obtained_marks * assessment.weightage / assessment.maximum_marks


def _is_pending(assessment) -> bool:
    return assessment.status != "exempted" and calculate_assessment_weighted_marks(assessment) is None


def _exemption_scale(assessments) -> Decimal:
    """Factor that spreads exempted weightage over the other assessments (1 when nothing is exempted)."""
    configured = sum((a.weightage for a in assessments), Decimal(0))
    effective = sum((a.weightage for a in assessments if a.status != "exempted"), Decimal(0))
    return configured / effective if effective else Decimal(1)


def _secured(assessments) -> Decimal:
    contributions = (calculate_assessment_weighted_marks(a) for a in assessments)
    return sum((c for c in contributions if c is not None), Decimal(0))


def _pending_weightage(assessments) -> Decimal:
    return sum((a.weightage for a in assessments if _is_pending(a)), Decimal(0))


def calculate_course_total(assessments) -> Decimal:
    """Marks secured so far, out of the configured total weightage (normally 100)."""
    return _secured(assessments) * _exemption_scale(assessments)


def calculate_maximum_possible_marks(assessments) -> Decimal:
    """Final marks if every pending assessment is scored in full."""
    return (_secured(assessments) + _pending_weightage(assessments)) * _exemption_scale(assessments)


def calculate_projected_marks(assessments) -> Decimal | None:
    """Final marks if pending assessments are scored at the same rate as the completed ones."""
    secured = _secured(assessments)
    completed_weightage = sum(
        (a.weightage for a in assessments if calculate_assessment_weighted_marks(a) is not None), Decimal(0)
    )
    if not completed_weightage:
        return None
    projected = secured + _pending_weightage(assessments) * secured / completed_weightage
    return projected * _exemption_scale(assessments)


def calculate_required_marks(assessments, target_marks: Decimal, grade: str = "") -> GradeTarget:
    """What the pending assessments must score for the course to reach `target_marks`.

    With one pending assessment this is the workbook formula
    (target - existing weighted marks) x maximum / weightage.
    With several, the same percentage is required on each of them.
    """
    def result(status, percentage=None, marks=None):
        return GradeTarget(grade, target_marks, status, percentage, marks or {})

    if sum((a.weightage for a in assessments), Decimal(0)) != FULL_WEIGHTAGE:
        return result("pending_configuration")

    still_needed = target_marks / _exemption_scale(assessments) - _secured(assessments)
    pending_weightage = _pending_weightage(assessments)
    if still_needed <= 0:
        return result("already_achieved")
    if still_needed > pending_weightage:
        return result("not_achievable")

    percentage = still_needed / pending_weightage * 100
    marks = {a.name: a.maximum_marks * percentage / 100 for a in assessments if _is_pending(a)}
    return result("achievable", percentage, marks)


def predict_course_grade(marks: Decimal, grade_bands, round_marks: bool = False):
    """The highest grade band whose minimum is met, or None if none is."""
    if round_marks:
        marks = marks.quantize(Decimal(1), rounding=ROUND_HALF_UP)
    reachable = [b for b in grade_bands if b.minimum_marks is not None and marks >= b.minimum_marks]
    return max(reachable, key=lambda b: b.minimum_marks, default=None)


def analyse_course(assessments, grade_bands, round_marks: bool = False) -> CourseAnalysis:
    """Everything the course screen needs, in one call."""
    weightage_total = sum((a.weightage for a in assessments), Decimal(0))
    is_complete = weightage_total == FULL_WEIGHTAGE

    projected = calculate_projected_marks(assessments)
    predicted = predict_course_grade(projected, grade_bands, round_marks) if is_complete and projected is not None else None

    target_bands = sorted(
        (b for b in grade_bands if b.is_passing and b.minimum_marks is not None),
        key=lambda b: b.minimum_marks,
        reverse=True,
    )
    targets = [calculate_required_marks(assessments, band.minimum_marks, band.grade) for band in target_bands]

    return CourseAnalysis(
        weightage_total=weightage_total,
        is_configuration_complete=is_complete,
        current_marks=calculate_course_total(assessments),
        maximum_possible_marks=calculate_maximum_possible_marks(assessments),
        projected_marks=projected,
        predicted_grade=predicted.grade if predicted else None,
        predicted_grade_point=predicted.grade_point if predicted else None,
        pending_assessments=[a.name for a in assessments if _is_pending(a)],
        targets=targets,
    )
