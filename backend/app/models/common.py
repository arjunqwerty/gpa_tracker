"""Pieces shared by every collection."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from beanie import Document, Replace, Save, before_event
from bson import Decimal128
from pydantic import AliasGenerator, BeforeValidator, ConfigDict, Field, PlainSerializer, StringConstraints


def _to_decimal(value):
    return value.to_decimal() if isinstance(value, Decimal128) else value


# A Decimal that is stored in MongoDB as Decimal128 and sent to the browser as a
# JSON number. Calculations always use the Decimal; the float is presentation only.
Dec = Annotated[Decimal, BeforeValidator(_to_decimal), PlainSerializer(float, return_type=float, when_used="json")]


# Text limits shared by every model, so a typo or a pasted page cannot store a 10 MB title.
# Surrounding spaces are trimmed; an empty value is rejected.
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Code = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampedDocument(Document):
    # MongoDB stores the id as "_id"; the API sends it as "id".
    model_config = ConfigDict(
        alias_generator=AliasGenerator(alias=lambda name: "_id" if name == "id" else name, serialization_alias=lambda name: name)
    )

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @before_event(Replace, Save)
    def _touch(self):
        self.updated_at = utc_now()
