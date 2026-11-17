"""Course calculations, checked against the reference workbook (marks.xlsx)."""
from decimal import Decimal as D

from app.engine.marks import (
    Assessment,
    GradeBand,
    analyse_course,
    calculate_assessment_weighted_marks,
    calculate_course_total,
    calculate_maximum_possible_marks,
    calculate_required_marks,
    predict_course_grade,
)

VIT_BANDS = [
    GradeBand("S", D(10), D(90)),
    GradeBand("A", D(9), D(80)),
    GradeBand("B", D(8), D(70)),
    GradeBand("C", D(7), D(60)),
    GradeBand("D", D(6), D(55)),
    GradeBand("E", D(5), D(50)),
    GradeBand("F", D(0), D(0), is_passing=False),
    GradeBand("P", D(0), None),
]


def done(name, maximum, weightage, obtained):
    return Assessment(name, D(maximum), D(weightage), D(str(obtained)), "completed")


def pending(name, maximum, weightage):
    return Assessment(name, D(maximum), D(weightage))


# Semester 4 "Complex" course, without and with the FAT.
COMPLEX_BEFORE_FAT = [
    done("CAT 1", 50, 15, 36),
    done("CAT 2", 50, 15, 46),
    done("DA 1", 10, 10, 9),
    done("DA 2", 10, 10, 9),
    done("DA 3", 10, 10, 9),
    pending("FAT", 100, 40),
]
COMPLEX = COMPLEX_BEFORE_FAT[:-1] + [done("FAT", 100, 40, 64)]


def target(targets, grade):
    return next(t for t in targets if t.grade == grade)


def test_weighted_marks_formula():
    assert calculate_assessment_weighted_marks(done("CAT 1", 50, 15, 36)) == D("10.8")
    assert calculate_assessment_weighted_marks(done("DA 2", 10, 10, "8.63")) == D("8.63")  # fractional marks


def test_pending_is_not_zero_but_absent_is():
    assert calculate_assessment_weighted_marks(pending("FAT", 100, 40)) is None
    assert calculate_assessment_weighted_marks(Assessment("FAT", D(100), D(40), None, "absent")) == 0


def test_course_totals_match_workbook():
    assert calculate_course_total(COMPLEX) == D("77.2")
    robotics = [done("CAT 1", 50, 15, "40.5"), done("CAT 2", 50, 15, 26), done("DA 1", 10, 10, 8),
                done("DA 2", 10, 10, 9), done("Quiz 1", 10, 10, 8), done("FAT", 100, 40, 41)]
    assert calculate_course_total(robotics) == D("61.35")
    daa = [done("CAT 1", 50, 15, 22), done("CAT 2", 50, 15, "37.5"), done("DA 1", 10, 10, 10),
           done("DA 2", 10, 10, "8.63"), done("DA 3", 10, 10, "8.5"), done("FAT", 100, 40, 80)]
    assert calculate_course_total(daa) == D("76.98")


def test_required_fat_marks_single_pending_matches_workbook_formula():
    # (threshold - existing weighted) x FAT max / FAT weightage, existing = 51.6
    analysis = analyse_course(COMPLEX_BEFORE_FAT, VIT_BANDS)
    assert analysis.current_marks == D("51.6")
    assert analysis.maximum_possible_marks == D("91.6")
    assert target(analysis.targets, "S").required_marks == {"FAT": D(96)}
    assert target(analysis.targets, "A").required_marks == {"FAT": D(71)}
    assert target(analysis.targets, "C").required_marks == {"FAT": D(21)}
    assert target(analysis.targets, "E").status == "already_achieved"


def test_target_statuses():
    assert calculate_required_marks(COMPLEX, D(70)).status == "already_achieved"
    assert calculate_required_marks(COMPLEX, D(90)).status == "not_achievable"  # nothing left to score
    assert calculate_required_marks(COMPLEX_BEFORE_FAT, D(95)).status == "not_achievable"  # needs 108.5/100
    assert calculate_required_marks(COMPLEX_BEFORE_FAT[:-1], D(90)).status == "pending_configuration"  # 60% configured


def test_multiple_pending_assessments_share_the_requirement():
    # Semester 7 "Project 1": the workbook only used Review 3 here, which is wrong.
    project = [done("Review 1", 5, 5, 5), done("Review 2", 40, 40, 32), pending("Review 3", 30, 30),
               pending("Review 4", 20, 20), done("Project Report", 5, 5, 5)]
    s = calculate_required_marks(project, D(90))
    assert s.status == "achievable"
    assert s.required_percentage == D(96)
    assert s.required_marks == {"Review 3": D("28.8"), "Review 4": D("19.2")}
    assert calculate_maximum_possible_marks(project) == D(92)


def test_exempted_weightage_is_redistributed():
    course = [done("Theory", 50, 50, 40), Assessment("Lab", D(50), D(50), None, "exempted")]
    assert calculate_course_total(course) == D(80)
    assert analyse_course(course, VIT_BANDS).predicted_grade == "A"


def test_prediction_uses_projected_marks():
    analysis = analyse_course(COMPLEX_BEFORE_FAT, VIT_BANDS)
    assert analysis.projected_marks == D(86)  # 86% on what is done so far
    assert (analysis.predicted_grade, analysis.predicted_grade_point) == ("A", D(9))
    assert analysis.pending_assessments == ["FAT"]


def test_no_prediction_without_marks_or_complete_configuration():
    assert analyse_course([pending("FAT", 100, 100)], VIT_BANDS).predicted_grade is None
    assert analyse_course(COMPLEX_BEFORE_FAT[:-1], VIT_BANDS).predicted_grade is None


def test_grade_boundaries_and_rounding():
    assert predict_course_grade(D("89.5"), VIT_BANDS).grade == "A"
    assert predict_course_grade(D("89.5"), VIT_BANDS, round_marks=True).grade == "S"
    assert predict_course_grade(D("42"), VIT_BANDS).grade == "F"
    assert predict_course_grade(D("42"), VIT_BANDS[:6]) is None  # below every band
