"""Academic configuration: universities, programmes, curricula, course types and grading schemes.

Documents with `user_id = None` are shared reference data that every user can read.
"""
from decimal import Decimal

from beanie import PydanticObjectId
from pydantic import BaseModel, Field, field_validator
from pymongo import IndexModel

from app.models.common import Code, Dec, Name, TimestampedDocument


class University(TimestampedDocument):
    name: str
    short_name: str

    class Settings:
        name = "universities"
        indexes = [IndexModel("short_name", unique=True)]


class Programme(TimestampedDocument):
    university_id: PydanticObjectId
    name: str
    degree_type: str
    duration_semesters: int = Field(ge=1)

    class Settings:
        name = "programmes"
        indexes = [IndexModel([("university_id", 1), ("name", 1)], unique=True)]


class CreditCategory(BaseModel):
    code: Code
    name: Name
    required_credits: Dec = Field(default=Decimal(0), ge=0, le=1000)


class TemplateAssessment(BaseModel):
    name: Name
    maximum_marks: Dec = Field(gt=0, le=1000)
    weightage: Dec = Field(ge=0, le=100)


class CourseTemplate(BaseModel):
    template_id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    course_code: Code
    title: Name
    course_type_code: Code | None = None
    credits: Dec = Field(ge=0, le=50)
    category_code: Code | None = None
    counts_towards_gpa: bool = True
    counts_towards_earned_credits: bool = True
    counts_towards_requirement: bool = True
    default_assessments: list[TemplateAssessment] = []


class CurriculumVersion(TimestampedDocument):
    """A programme's credit requirements per category, plus its course templates."""
    user_id: PydanticObjectId | None = None  # None = shared
    programme_id: PydanticObjectId | None = None
    version_name: Name
    effective_year: int | None = None
    categories: list[CreditCategory] = []
    course_templates: list[CourseTemplate] = []

    @property
    def total_required_credits(self) -> Decimal:
        return sum((c.required_credits for c in self.categories), Decimal(0))

    class Settings:
        name = "curriculum_versions"
        indexes = [IndexModel([("user_id", 1), ("programme_id", 1), ("version_name", 1)], unique=True)]


class CourseType(TimestampedDocument):
    user_id: PydanticObjectId | None = None  # None = shared
    code: Code
    name: Name

    class Settings:
        name = "course_types"
        indexes = [IndexModel([("user_id", 1), ("code", 1)], unique=True)]


class GradeEntry(BaseModel):
    grade: Code
    grade_point: Dec = Field(ge=0, le=100)
    minimum_marks: Dec | None = Field(default=None, ge=0, le=100)  # None = only awarded, never predicted (e.g. P, N)
    maximum_marks: Dec | None = Field(default=None, ge=0, le=100)
    is_passing: bool = True


class GradingSchemeFields(BaseModel):
    """What the user can edit on a grading scheme (also the request body)."""
    name: Name
    entries: list[GradeEntry]  # in display order, best grade first

    @field_validator("entries")
    @classmethod
    def _grades_are_unique(cls, entries):
        grades = [e.grade for e in entries]
        if not grades or len(grades) != len(set(grades)):
            raise ValueError("A grading scheme needs at least one grade, and each grade label must be different")
        return entries


class GradingScheme(TimestampedDocument, GradingSchemeFields):
    """Versioned: editing a scheme saves a new version and archives the old one,
    so results recorded against the old version never change."""
    user_id: PydanticObjectId
    scheme_key: str  # the same for every version of one scheme
    version: int = 1
    is_archived: bool = False

    def entry_for(self, grade: str) -> GradeEntry | None:
        return next((e for e in self.entries if e.grade == grade), None)

    class Settings:
        name = "grading_schemes"
        indexes = [IndexModel([("user_id", 1), ("scheme_key", 1), ("version", -1)], unique=True)]
