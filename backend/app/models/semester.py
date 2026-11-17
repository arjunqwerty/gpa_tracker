from typing import Literal

from beanie import PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import IndexModel

from app.models.common import Name, TimestampedDocument

SEMESTER_TYPE_ORDER = {"regular": 0, "summer": 1, "other": 2}


class SemesterFields(BaseModel):
    """What the user can set on a semester (also the request body for create/update)."""
    semester_number: int = Field(ge=1, le=30)
    semester_type: Literal["regular", "summer", "other"] = "regular"
    label: Name  # e.g. "Semester 4" or "Summer 2024"
    academic_year: str | None = Field(default=None, max_length=20)  # e.g. "2023-24"
    status: Literal["planned", "active", "completed"] = "active"


class Semester(TimestampedDocument, SemesterFields):
    user_id: PydanticObjectId

    @property
    def sort_key(self):
        """Chronological order: a summer term numbered 5 comes after regular semester 5."""
        return self.semester_number, SEMESTER_TYPE_ORDER[self.semester_type]

    class Settings:
        name = "semesters"
        indexes = [IndexModel([("user_id", 1), ("semester_number", 1), ("semester_type", 1)])]
