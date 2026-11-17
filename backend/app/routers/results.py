"""Official results and grade history.

A result is first recorded as provisional and then confirmed. Grade history is
every course that has an official result; a past result typed in by hand is a
course with a confirmed result and no assessments. Every change is audited.
"""
import re
from datetime import datetime
from typing import Literal

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.database import transaction
from app.models import AuditLog, Course, GradingScheme
from app.models.course import CourseFields, OfficialResult
from app.ownership import CurrentUser, check_course_references, get_owned

router = APIRouter(prefix="/api", tags=["results"])


class ResultIn(BaseModel):
    grade: str
    exam_month: datetime | None = None
    result_date: datetime | None = None
    source: Literal["manual", "generated"] = "manual"  # "generated" = accepted the predicted grade


class HistoryEntryIn(CourseFields):
    grade: str
    exam_month: datetime | None = None
    result_date: datetime | None = None


class HistoryPage(BaseModel):
    total: int
    items: list[Course]


async def _record_result(course: Course, user, grade: str, **details):
    """Sets course.official_result from `grade`, using the course's grading scheme."""
    scheme_id = course.grading_scheme_id or user.settings.default_grading_scheme_id
    course.grading_scheme_id = scheme_id
    scheme = await get_owned(GradingScheme, scheme_id, user)
    try:
        course.official_result = OfficialResult.snapshot(course, scheme, grade, **details)
    except ValueError as error:
        raise HTTPException(422, str(error))


async def _save_audited(course: Course, user, action: str, before: Course | None) -> Course:
    async with transaction() as session:
        await course.save(session=session)
        await AuditLog.record(user, course, action, before, course, session)
    return course


async def _history_course(course_id: PydanticObjectId, user) -> Course:
    course = await get_owned(Course, course_id, user)
    if course.official_result is None:
        raise HTTPException(404, "This course is not in the grade history")
    return course


# --- Official result of a tracked course ---

@router.put("/courses/{course_id}/official-result")
async def set_official_result(course_id: PydanticObjectId, body: ResultIn, user: CurrentUser) -> Course:
    """Records (or corrects) the declared grade as provisional. Confirm it separately."""
    course = await get_owned(Course, course_id, user)
    before = course.model_copy(deep=True)
    await _record_result(course, user, body.grade, result_status="provisional", source=body.source,
                         exam_month=body.exam_month, result_date=body.result_date)
    return await _save_audited(course, user, "set_result", before)


@router.post("/courses/{course_id}/official-result/confirm")
async def confirm_official_result(course_id: PydanticObjectId, user: CurrentUser) -> Course:
    course = await _history_course(course_id, user)
    before = course.model_copy(deep=True)
    course.confirm_result()
    return await _save_audited(course, user, "confirm_result", before)


@router.delete("/courses/{course_id}/official-result")
async def remove_official_result(course_id: PydanticObjectId, user: CurrentUser) -> Course:
    course = await _history_course(course_id, user)
    if course.is_confirmed:
        raise HTTPException(409, "A confirmed result cannot be removed here. Use Correct confirmed result to record the right grade, or remove it on the Grade history page.")
    before = course.model_copy(deep=True)
    course.official_result = None
    return await _save_audited(course, user, "remove_result", before)


# --- Grade history ---

@router.get("/grade-history")
async def grade_history(
    user: CurrentUser,
    semester_id: PydanticObjectId | None = None,
    grade: str | None = None,
    course_type: str | None = None,
    category: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> HistoryPage:
    query = {"user_id": user.id, "official_result": {"$ne": None}}
    if semester_id:
        query["semester_id"] = semester_id
    if grade:
        query["official_result.grade"] = grade
    if course_type:
        query["course_type_code"] = course_type
    if category:
        query["official_result.category_code"] = category
    if search:
        pattern = {"$regex": re.escape(search), "$options": "i"}
        query["$or"] = [{"course_code": pattern}, {"title": pattern}]

    found = Course.find(query)
    total = await found.count()
    items = await found.sort("official_result.exam_month", "course_code").skip((page - 1) * page_size).limit(page_size).to_list()
    return HistoryPage(total=total, items=items)


@router.post("/grade-history", status_code=201)
async def add_history_entry(body: HistoryEntryIn, user: CurrentUser) -> Course:
    """A past result entered by hand: saved straight away as confirmed."""
    await check_course_references(body, user)
    course = Course(user_id=user.id, source="manual", **body.model_dump(exclude={"grade", "exam_month", "result_date"}))
    await _record_result(course, user, body.grade, result_status="provisional", source="manual",
                         exam_month=body.exam_month, result_date=body.result_date)
    course.confirm_result()
    async with transaction() as session:
        await course.insert(session=session)
        await AuditLog.record(user, course, "create", after=course, session=session)
    return course


@router.put("/grade-history/{course_id}")
async def update_history_entry(course_id: PydanticObjectId, body: HistoryEntryIn, user: CurrentUser) -> Course:
    course = await _history_course(course_id, user)
    await check_course_references(body, user)
    before = course.model_copy(deep=True)
    for field in CourseFields.model_fields:
        setattr(course, field, getattr(body, field))
    await _record_result(course, user, body.grade, result_status="provisional", source=course.official_result.source,
                         exam_month=body.exam_month, result_date=body.result_date)
    course.confirm_result()
    return await _save_audited(course, user, "update_result", before)


@router.delete("/grade-history/{course_id}", status_code=204)
async def delete_history_entry(course_id: PydanticObjectId, user: CurrentUser):
    """Removes the result. A hand-entered course (no assessments) is removed completely."""
    course = await _history_course(course_id, user)
    async with transaction() as session:
        if course.assessments:
            before = course.model_copy(deep=True)
            course.official_result, course.status = None, "in_progress"
            await course.save(session=session)
            await AuditLog.record(user, course, "remove_result", before, course, session)
        else:
            await course.delete(session=session)
            await AuditLog.record(user, course, "delete", before=course, session=session)
