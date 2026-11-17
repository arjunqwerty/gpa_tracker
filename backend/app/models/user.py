from beanie import PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import IndexModel

from app.models.common import Dec, Name, TimestampedDocument


class Profile(BaseModel):
    full_name: Name = "Student"
    university_id: PydanticObjectId | None = None
    programme_id: PydanticObjectId | None = None
    curriculum_version_id: PydanticObjectId | None = None  # drives credit tracking and templates
    specialisation: Name | None = None
    admission_year: int | None = None
    graduation_year: int | None = None


class UserSettings(BaseModel):
    default_grading_scheme_id: PydanticObjectId | None = None  # used for new courses
    round_marks_before_grading: bool = False  # outstanding academic decision 2
    target_cgpa: Dec | None = Field(default=None, gt=0, le=100)


class User(TimestampedDocument):
    email: str | None = None  # stored lower-case
    password_hash: str | None = None  # Argon2id
    is_active: bool = True
    # The account used before login existed (no email or password). The first person to
    # register may claim it, keeping all of its data.
    is_local: bool = False
    profile: Profile = Field(default_factory=Profile)
    settings: UserSettings = Field(default_factory=UserSettings)

    class Settings:
        name = "users"
        indexes = [IndexModel("email", unique=True, partialFilterExpression={"email": {"$type": "string"}})]
