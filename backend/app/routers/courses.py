"""Courses and their assessments."""
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import transaction
from app.models import AuditLog, Course, CurriculumVersion, Semester
from app.models.configuration import CourseTemplate
from app.models.course import AssessmentFields, CourseAssessment, CourseFields
from app.ownership import CurrentUser, check_course_references, get_owned, get_visible

router = APIRouter(prefix="/api/courses", tags=["courses"])

# Course fields that a curriculum template provides (code, title, credits, category, ...).
TEMPLATE_FIELDS = set(CourseFields.model_fields) & set(CourseTemplate.model_fields)


class CourseCreate(CourseFields):
    assessments: list[AssessmentFields] = []


class FromTemplatesIn(BaseModel):
    semester_id: PydanticObjectId
    curriculum_version_id: PydanticObjectId
    template_ids: list[PydanticObjectId]


class DuplicateIn(BaseModel):
    semester_id: PydanticObjectId | None = None  # defaults to the original's semester


def _find_assessment(course: Course, assessment_id: PydanticObjectId) -> int:
    for index, assessment in enumerate(course.assessments):
        if assessment.id == assessment_id:
            return index
    raise HTTPException(404, "Assessment not found")


# --- Courses ---

@router.get("")
async def list_courses(user: CurrentUser, semester_id: PydanticObjectId | None = None) -> list[Course]:
    query = {"user_id": user.id}
    if semester_id:
        query["semester_id"] = semester_id
    return await Course.find(query).sort("course_code").to_list()


@router.post("", status_code=201)
async def create_course(body: CourseCreate, user: CurrentUser) -> Course:
    await check_course_references(body, user)
    course = Course(user_id=user.id, **body.model_dump())
    course.grading_scheme_id = course.grading_scheme_id or user.settings.default_grading_scheme_id
    return await course.insert()


@router.post("/from-template", status_code=201)
async def create_courses_from_templates(body: FromTemplatesIn, user: CurrentUser) -> list[Course]:
    """Copies templates into the semester. Later template edits never touch these courses."""
    await get_owned(Semester, body.semester_id, user)
    curriculum = await get_visible(CurriculumVersion, body.curriculum_version_id, user)
    templates = {t.template_id: t for t in curriculum.course_templates}
    if missing := [str(i) for i in body.template_ids if i not in templates]:
        raise HTTPException(404, f"Templates not found in this curriculum: {', '.join(missing)}")

    courses = []
    for template_id in body.template_ids:
        template = templates[template_id]
        course = Course(
            user_id=user.id,
            semester_id=body.semester_id,
            template_id=template_id,
            source="template",
            grading_scheme_id=user.settings.default_grading_scheme_id,
            assessments=[a.model_dump() for a in template.default_assessments],
            **template.model_dump(include=TEMPLATE_FIELDS),
        )
        courses.append(await course.insert())
    return courses


@router.get("/{course_id}")
async def get_course(course_id: PydanticObjectId, user: CurrentUser) -> Course:
    return await get_owned(Course, course_id, user)


@router.put("/{course_id}")
async def update_course(course_id: PydanticObjectId, body: CourseFields, user: CurrentUser) -> Course:
    course = await get_owned(Course, course_id, user)
    await check_course_references(body, user)
    for field, value in body:
        setattr(course, field, value)
    return await course.save()


@router.delete("/{course_id}", status_code=204)
async def delete_course(course_id: PydanticObjectId, user: CurrentUser):
    course = await get_owned(Course, course_id, user)
    if course.is_confirmed:
        raise HTTPException(409, "This course has a confirmed result, so it cannot be deleted. Remove the result on the Grade history page first.")
    async with transaction() as session:
        await course.delete(session=session)
        await AuditLog.record(user, course, "delete", before=course, session=session)


@router.post("/{course_id}/duplicate", status_code=201)
async def duplicate_course(course_id: PydanticObjectId, body: DuplicateIn, user: CurrentUser) -> Course:
    """Copies the course set-up (details and assessment structure) without any marks or result."""
    original = await get_owned(Course, course_id, user)
    fields = CourseFields(**original.model_dump()).model_dump()
    fields["status"] = "in_progress"
    if body.semester_id:
        await get_owned(Semester, body.semester_id, user)
        fields["semester_id"] = body.semester_id
    structure = [a.model_dump(include={"name", "maximum_marks", "weightage", "allow_over_max"}) for a in original.assessments]
    return await Course(user_id=user.id, assessments=structure, **fields).insert()


# --- Assessments (stored inside the course document) ---

@router.get("/{course_id}/assessments")
async def list_assessments(course_id: PydanticObjectId, user: CurrentUser) -> list[CourseAssessment]:
    return (await get_owned(Course, course_id, user)).assessments


@router.post("/{course_id}/assessments", status_code=201)
async def add_assessment(course_id: PydanticObjectId, body: AssessmentFields, user: CurrentUser) -> Course:
    course = await get_owned(Course, course_id, user)
    course.assessments.append(CourseAssessment(**body.model_dump()))
    return await course.save()


@router.put("/{course_id}/assessments/{assessment_id}")
async def update_assessment(
    course_id: PydanticObjectId, assessment_id: PydanticObjectId, body: AssessmentFields, user: CurrentUser
) -> Course:
    course = await get_owned(Course, course_id, user)
    course.assessments[_find_assessment(course, assessment_id)] = CourseAssessment(id=assessment_id, **body.model_dump())
    return await course.save()


@router.delete("/{course_id}/assessments/{assessment_id}")
async def delete_assessment(course_id: PydanticObjectId, assessment_id: PydanticObjectId, user: CurrentUser) -> Course:
    course = await get_owned(Course, course_id, user)
    del course.assessments[_find_assessment(course, assessment_id)]
    return await course.save()
