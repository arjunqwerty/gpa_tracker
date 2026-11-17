"""A course a student takes, with its assessments and (once declared) its official result.

Grade history is simply every course that has an `official_result`; manual
history entries are courses without assessments. One collection means a
course can never be "completed" twice by accident.
"""
from datetime import datetime
from typing import Literal

from beanie import PydanticObjectId
from pydantic import BaseModel, Field, model_validator
from pymongo import IndexModel

from app.models.common import Code, Dec, Name, TimestampedDocument, utc_now


class AssessmentFields(BaseModel):
    name: Name
    maximum_marks: Dec = Field(gt=0, le=1000)
    weightage: Dec = Field(ge=0, le=100)
    obtained_marks: Dec | None = Field(default=None, ge=0, le=10000)
    status: Literal["pending", "completed", "absent", "exempted"] = "pending"
    allow_over_max: bool = False
    assessment_date: datetime | None = None

    @model_validator(mode="after")
    def _marks_within_maximum(self):
        if self.obtained_marks is not None and self.obtained_marks > self.maximum_marks and not self.allow_over_max:
            raise ValueError(f"{self.name}: obtained marks cannot exceed the maximum of {self.maximum_marks}")
        return self


class CourseAssessment(AssessmentFields):
    id: PydanticObjectId = Field(default_factory=PydanticObjectId)


class OfficialResult(BaseModel):
    """The declared grade. Credits, category and GPA eligibility are copied here when
    the result is recorded so later edits to the course never rewrite history."""
    grade: str
    grade_point: Dec
    is_passing: bool
    result_status: Literal["provisional", "confirmed"]
    credits: Dec
    category_code: str | None
    counts_towards_gpa: bool
    grading_scheme_id: PydanticObjectId | None = None
    grading_scheme_version: int | None = None
    exam_month: datetime | None = None
    result_date: datetime | None = None
    source: Literal["manual", "import", "generated"] = "manual"
    confirmed_at: datetime | None = None

    @classmethod
    def snapshot(cls, course, scheme, grade: str, **details) -> "OfficialResult":
        """Records `grade` for `course`, copying everything that must not change later.
        `details` are the remaining fields (result_status, source, exam_month, ...)."""
        entry = scheme.entry_for(grade)
        if entry is None:
            raise ValueError(f"Grade '{grade}' is not part of the grading scheme '{scheme.name}'")
        return cls(
            grade=entry.grade, grade_point=entry.grade_point, is_passing=entry.is_passing,
            credits=course.credits, category_code=course.category_code, counts_towards_gpa=course.counts_towards_gpa,
            grading_scheme_id=scheme.id, grading_scheme_version=scheme.version, **details,
        )


class CourseFields(BaseModel):
    """What the user can edit on a course (also the request body for create/update)."""
    semester_id: PydanticObjectId
    course_code: Code
    title: Name
    course_type_code: Code | None = None
    credits: Dec = Field(ge=0, le=50)
    category_code: Code | None = None

    counts_towards_gpa: bool = True
    counts_towards_earned_credits: bool = True
    counts_towards_requirement: bool = True

    status: Literal["planned", "in_progress", "completed", "failed", "withdrawn"] = "in_progress"
    grading_scheme_id: PydanticObjectId | None = None  # defaults to the user's default scheme
    attempt: int = Field(default=1, ge=1, le=20)  # a repeated course is a new course with attempt + 1


class Course(TimestampedDocument, CourseFields):
    user_id: PydanticObjectId
    template_id: PydanticObjectId | None = None
    source: Literal["manual", "template", "import"] = "manual"

    assessments: list[CourseAssessment] = []
    official_result: OfficialResult | None = None

    @property
    def is_confirmed(self) -> bool:
        return self.official_result is not None and self.official_result.result_status == "confirmed"

    def confirm_result(self):
        self.official_result.result_status = "confirmed"
        self.official_result.confirmed_at = utc_now()
        self.status = "completed" if self.official_result.is_passing else "failed"

    class Settings:
        name = "courses"
        indexes = [
            IndexModel([("user_id", 1), ("semester_id", 1)]),
            # No two official results for the same course attempt.
            IndexModel(
                [("user_id", 1), ("course_code", 1), ("attempt", 1)],
                unique=True,
                partialFilterExpression={"official_result": {"$type": "object"}},
                name="one_result_per_attempt",
            ),
        ]
