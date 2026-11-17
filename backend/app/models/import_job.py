"""An uploaded Excel file waiting to be committed (preview + validation report)."""
from datetime import datetime, timedelta
from typing import Any, Literal

from beanie import PydanticObjectId
from pydantic import Field
from pymongo import IndexModel

from app.models.common import TimestampedDocument, utc_now


def _in_a_week() -> datetime:
    return utc_now() + timedelta(days=7)


class ImportJob(TimestampedDocument):
    user_id: PydanticObjectId
    filename: str
    status: Literal["validated", "failed", "committed"]
    preview: dict[str, Any]  # what will be created, as plain JSON
    errors: list[str] = []  # any error blocks the commit
    warnings: list[str] = []
    expires_at: datetime | None = Field(default_factory=_in_a_week)  # cleared once committed
    committed_at: datetime | None = None

    class Settings:
        name = "import_jobs"
        # MongoDB deletes uncommitted jobs once expires_at has passed.
        indexes = [IndexModel("expires_at", expireAfterSeconds=0), IndexModel([("user_id", 1), ("created_at", -1)])]
