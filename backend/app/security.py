"""Passwords, login tokens, auth cookies and the login rate limit.

A login gives the browser two httpOnly cookies:
- access_token: a JWT naming the user, valid for 15 minutes, sent with every /api request.
- refresh_token: a random token, valid for 30 days, sent only to /api/auth. It is swapped
  for a new pair at /api/auth/refresh, and each refresh token works once.
"""
import hashlib
import os
import secrets
import time
from collections import defaultdict
from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import HTTPException, Request, Response

from app.models import AuthToken, User
from app.models.common import utc_now

# Without a fixed secret every restart logs everyone out after at most 15 minutes (the refresh
# token still works, so the browser recovers silently). Set it in production.
SECRET_KEY = os.getenv("GPA_TRACKER_SECRET_KEY") or secrets.token_urlsafe(32)
COOKIE_SECURE = os.getenv("GPA_TRACKER_COOKIE_SECURE", "false") == "true"  # true when served over HTTPS
ACCESS_LIFETIME = timedelta(minutes=15)
REFRESH_LIFETIME = timedelta(days=30)
RESET_LIFETIME = timedelta(hours=1)
REUSE_GRACE = timedelta(minutes=1)
ATTEMPTS_PER_MINUTE = int(os.getenv("GPA_TRACKER_AUTH_ATTEMPTS_PER_MINUTE", "10"))

_password_hasher = PasswordHasher()  # Argon2id with the library's recommended parameters


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def password_matches(user: User, password: str) -> bool:
    try:
        return user.password_hash is not None and _password_hasher.verify(user.password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


# --- Access tokens (JWT) ---

def create_access_token(user: User) -> str:
    return jwt.encode({"sub": str(user.id), "exp": utc_now() + ACCESS_LIFETIME}, SECRET_KEY, algorithm="HS256")


def user_id_from_access_token(token: str) -> str | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])["sub"]
    except jwt.PyJWTError:
        return None


# --- One-time tokens (refresh and password reset) ---

def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def issue_token(user: User, kind: str, lifetime: timedelta) -> str:
    token = secrets.token_urlsafe(32)
    await AuthToken(user_id=user.id, kind=kind, token_hash=_hash(token), expires_at=utc_now() + lifetime).insert()
    return token


async def use_token(token: str, kind: str) -> AuthToken | None:
    """Marks the token used and returns it, or None if it is unknown, expired or already used."""
    stored = await AuthToken.find_one({"token_hash": _hash(token), "kind": kind})
    if stored is None or stored.expires_at < utc_now():
        return None
    if stored.used_at is not None:
        # Two browser tabs may refresh at the same moment; a reuse much later means a stolen
        # copy is being replayed, so every session of this user is ended.
        if kind == "refresh" and utc_now() - stored.used_at > REUSE_GRACE:
            await revoke_refresh_tokens(stored.user_id)
        return None
    stored.used_at = utc_now()
    await stored.save()
    return stored


async def revoke_refresh_tokens(user_id):
    await AuthToken.find({"user_id": user_id, "kind": "refresh", "used_at": None}).update({"$set": {"used_at": utc_now()}})


# --- Cookies ---

async def log_in(response: Response, user: User):
    """Starts a session: sets fresh access and refresh cookies."""
    cookie = {"httponly": True, "secure": COOKIE_SECURE, "samesite": "strict"}
    response.set_cookie("access_token", create_access_token(user), path="/api",
                        max_age=int(ACCESS_LIFETIME.total_seconds()), **cookie)
    response.set_cookie("refresh_token", await issue_token(user, "refresh", REFRESH_LIFETIME), path="/api/auth",
                        max_age=int(REFRESH_LIFETIME.total_seconds()), **cookie)


def clear_cookies(response: Response):
    response.delete_cookie("access_token", path="/api")
    response.delete_cookie("refresh_token", path="/api/auth")


# --- Rate limit for password guessing (per client address and endpoint, kept in memory) ---

_recent_attempts: dict[str, list[float]] = defaultdict(list)


def rate_limit(request: Request):
    key = f"{request.client.host if request.client else ''} {request.url.path}"
    now = time.monotonic()
    recent = [moment for moment in _recent_attempts[key] if now - moment < 60]
    if len(recent) >= ATTEMPTS_PER_MINUTE:
        raise HTTPException(429, "Too many attempts. Wait a minute and try again.")
    _recent_attempts[key] = recent + [now]
