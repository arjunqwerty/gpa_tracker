"""Login refresh tokens and password-reset tokens. Only a SHA-256 hash of each token is stored."""
from datetime import datetime
from typing import Literal

from beanie import PydanticObjectId
from pymongo import IndexModel

from app.models.common import TimestampedDocument


class AuthToken(TimestampedDocument):
    user_id: PydanticObjectId
    kind: Literal["refresh", "password_reset"]
    token_hash: str
    expires_at: datetime
    used_at: datetime | None = None  # a token works once; reusing a refresh token logs the user out everywhere

    class Settings:
        name = "auth_tokens"
        # MongoDB deletes tokens once expires_at has passed.
        indexes = [IndexModel("token_hash", unique=True), IndexModel("expires_at", expireAfterSeconds=0),
                   IndexModel("user_id")]
