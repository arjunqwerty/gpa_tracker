"""A record of every change to official academic results."""
from typing import Any

from beanie import PydanticObjectId
from pymongo import IndexModel

from app.models.common import TimestampedDocument


def _as_json(document):
    return document.model_dump(mode="json") if document is not None else None


class AuditLog(TimestampedDocument):
    user_id: PydanticObjectId
    entity: str  # e.g. "course"
    entity_id: PydanticObjectId
    action: str  # e.g. "set_result", "confirm_result", "delete"
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None

    @classmethod
    async def record(cls, user, document, action: str, before=None, after=None, session=None):
        """`before` / `after` are documents (or None); they are stored as plain JSON."""
        await cls(user_id=user.id, entity=type(document).__name__.lower(), entity_id=document.id,
                  action=action, before=_as_json(before), after=_as_json(after)).insert(session=session)

    class Settings:
        name = "audit_log"
        indexes = [IndexModel([("user_id", 1), ("entity_id", 1), ("created_at", -1)])]
