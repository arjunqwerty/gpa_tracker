from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException

from app.database import transaction
from app.models import Course, Semester
from app.models.semester import SemesterFields
from app.ownership import CurrentUser, get_owned

router = APIRouter(prefix="/api/semesters", tags=["semesters"])


@router.get("")
async def list_semesters(user: CurrentUser) -> list[Semester]:
    semesters = await Semester.find(Semester.user_id == user.id).to_list()
    return sorted(semesters, key=lambda s: s.sort_key)


@router.post("", status_code=201)
async def create_semester(body: SemesterFields, user: CurrentUser) -> Semester:
    return await Semester(user_id=user.id, **body.model_dump()).insert()


@router.get("/{semester_id}")
async def get_semester(semester_id: PydanticObjectId, user: CurrentUser) -> Semester:
    return await get_owned(Semester, semester_id, user)


@router.put("/{semester_id}")
async def update_semester(semester_id: PydanticObjectId, body: SemesterFields, user: CurrentUser) -> Semester:
    semester = await get_owned(Semester, semester_id, user)
    for field, value in body:
        setattr(semester, field, value)
    return await semester.save()


@router.delete("/{semester_id}", status_code=204)
async def delete_semester(semester_id: PydanticObjectId, user: CurrentUser):
    """Deletes the semester and its courses, unless one of them has a confirmed result."""
    semester = await get_owned(Semester, semester_id, user)
    courses = await Course.find(Course.user_id == user.id, Course.semester_id == semester.id).to_list()
    if any(course.is_confirmed for course in courses):
        raise HTTPException(409, "This semester has courses with confirmed results, so it cannot be deleted. Move those courses to another semester, or remove their results on the Grade history page, first.")
    async with transaction() as session:
        await Course.find(Course.user_id == user.id, Course.semester_id == semester.id, session=session).delete(session=session)
        await semester.delete(session=session)
