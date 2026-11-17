"""Read-only calculations: course marks analysis, GPA, CGPA, target CGPA and credit progress.

Responses are engine dataclasses; FastAPI turns their Decimals into JSON numbers.
"""
from decimal import Decimal

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.models import Course, Semester
from app.ownership import CurrentUser, get_owned
from app.services import calculations

router = APIRouter(prefix="/api", tags=["calculations"])


class SimulationIn(BaseModel):
    marks: dict[PydanticObjectId, Decimal]  # assessment id -> hypothetical obtained marks


class TargetCgpaIn(BaseModel):
    target_cgpa: Decimal = Field(gt=0, le=100)
    remaining_credits: Decimal | None = Field(default=None, ge=0, le=1000)  # defaults to the curriculum's remaining credits


@router.get("/courses/{course_id}/calculation")
async def course_calculation(course_id: PydanticObjectId, user: CurrentUser):
    course = await get_owned(Course, course_id, user)
    return calculations.analyse_course(course, await calculations.load_schemes(user), user)


@router.post("/courses/{course_id}/simulate")
async def simulate_course(course_id: PydanticObjectId, body: SimulationIn, user: CurrentUser):
    """Analyses the course as if the given marks were scored. Nothing is saved."""
    course = await get_owned(Course, course_id, user)
    assessments = []
    for assessment in course.assessments:
        if assessment.id in body.marks:
            marks = body.marks[assessment.id]
            if marks < 0 or (marks > assessment.maximum_marks and not assessment.allow_over_max):
                raise HTTPException(422, f"{assessment.name}: marks must be between 0 and {assessment.maximum_marks}")
            assessment = assessment.model_copy(update={"obtained_marks": marks, "status": "completed"})
        assessments.append(assessment)
    return calculations.analyse_course(course, await calculations.load_schemes(user), user, assessments)


@router.get("/semesters/{semester_id}/gpa")
async def semester_gpa(semester_id: PydanticObjectId, user: CurrentUser):
    semester = await get_owned(Semester, semester_id, user)
    record = await calculations.load_record(user)
    return calculations.summarise_semester(semester, record.courses, record.schemes, user)


@router.get("/cgpa")
async def cgpa(user: CurrentUser):
    return calculations.cgpa_report(await calculations.load_record(user), user)


@router.post("/cgpa/target")
async def target_cgpa(body: TargetCgpaIn, user: CurrentUser):
    record = await calculations.load_record(user)
    remaining = body.remaining_credits
    if remaining is None:
        credits = calculations.credit_report(record, await calculations.user_curriculum(user))
        remaining = credits["remaining_credits"]
    return calculations.target_cgpa(record, user, body.target_cgpa, remaining)


@router.get("/credits/progress")
async def credit_progress(user: CurrentUser):
    record = await calculations.load_record(user)
    return calculations.credit_report(record, await calculations.user_curriculum(user))


@router.get("/dashboard/grade-distribution")
async def grade_distribution(user: CurrentUser):
    return calculations.grade_distribution(await calculations.load_record(user), user)
