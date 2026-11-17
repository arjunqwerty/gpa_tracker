"""Who is asking, and which documents they may touch.

MongoDB has no row-level security, so every read or write of user data must go
through a `user_id` filter. Routes use these helpers instead of fetching by id.
"""
from typing import Annotated

from beanie import PydanticObjectId
from fastapi import Cookie, Depends, HTTPException

from app.models import GradingScheme, Semester, User
from app.security import user_id_from_access_token


async def get_current_user(access_token: Annotated[str | None, Cookie()] = None) -> User:
    """The logged-in user, from the access_token cookie (see security.py), or 401."""
    user_id = user_id_from_access_token(access_token) if access_token else None
    user = await User.get(PydanticObjectId(user_id)) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(401, "You are not logged in. Log in to continue.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# What each kind of document is called in messages (the class name is used otherwise).
READABLE_NAMES = {"CurriculumVersion": "Curriculum", "GradingScheme": "Grading scheme", "ImportJob": "Import"}


def _not_found(model) -> HTTPException:
    name = READABLE_NAMES.get(model.__name__, model.__name__)
    return HTTPException(404, f"{name} not found. It may have been deleted; go back and reload the page.")


async def get_owned(model, document_id: PydanticObjectId, user: User):
    """A document that belongs to `user`, or 404. Use before any change."""
    document = await model.find_one({"_id": document_id, "user_id": user.id})
    if document is None:
        raise _not_found(model)
    return document


async def get_visible(model, document_id: PydanticObjectId, user: User):
    """A document that belongs to `user` or is shared (user_id is None), or 404. Use for reads."""
    document = await model.find_one({"_id": document_id, "user_id": {"$in": [None, user.id]}})
    if document is None:
        raise _not_found(model)
    return document


def visible_to(user: User) -> dict:
    """Query filter for documents the user owns plus shared ones."""
    return {"user_id": {"$in": [None, user.id]}}


async def check_course_references(course_fields, user: User):
    """A course may only point at the user's own semester and grading scheme."""
    await get_owned(Semester, course_fields.semester_id, user)
    if course_fields.grading_scheme_id:
        await get_owned(GradingScheme, course_fields.grading_scheme_id, user)
