"""Registration, login, logout, password reset and account management."""
import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Response
from pydantic import AfterValidator, BaseModel, Field

from app import security
from app.database import transaction
from app.models import ALL_DOCUMENTS, User
from app.ownership import CurrentUser
from app.seed import create_account

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = logging.getLogger(__name__)
APP_URL = os.getenv("GPA_TRACKER_APP_URL", "http://localhost:5173")  # used in password-reset links

Email = Annotated[str, Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254), AfterValidator(str.lower)]
Password = Annotated[str, Field(min_length=8, max_length=200)]
LimitedAttempts = [Depends(security.rate_limit)]


class Account(BaseModel):
    email: str
    full_name: str


def _account(user: User) -> Account:
    return Account(email=user.email, full_name=user.profile.full_name)


async def _unclaimed_local_user() -> User | None:
    """The data from before login existed, while nobody has registered yet (FR-14.4)."""
    if await User.find_one({"email": {"$type": "string"}}):
        return None
    return await User.find_one(User.is_local == True)  # noqa: E712 - Beanie needs ==


@router.get("/status")
async def status() -> dict:
    return {"local_data_available": await _unclaimed_local_user() is not None}


class Registration(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: Email
    password: Password
    claim_local_data: bool = False  # take over the data entered before login existed


@router.post("/register", status_code=201, dependencies=LimitedAttempts)
async def register(body: Registration, response: Response) -> Account:
    password_hash = security.hash_password(body.password)
    local_user = await _unclaimed_local_user() if body.claim_local_data else None
    if body.claim_local_data and local_user is None:
        raise HTTPException(409, "There is no earlier data to keep. Untick that option and register again.")
    if await User.find_one(User.email == body.email):
        raise HTTPException(409, "An account with this email already exists. Log in instead, or reset the password if you have forgotten it.")

    if local_user:
        local_user.email, local_user.password_hash, local_user.is_local = body.email, password_hash, False
        local_user.profile.full_name = body.full_name
        user = await local_user.save()
    else:
        user = await create_account(body.email, password_hash, body.full_name)
    await security.log_in(response, user)
    return _account(user)


class Login(BaseModel):
    email: Email
    password: str


@router.post("/login", dependencies=LimitedAttempts)
async def login(body: Login, response: Response) -> Account:
    user = await User.find_one(User.email == body.email)
    if user is None or not user.is_active or not security.password_matches(user, body.password):
        raise HTTPException(401, "Wrong email or password")
    await security.log_in(response, user)
    return _account(user)


@router.post("/refresh")
async def refresh(response: Response, refresh_token: Annotated[str | None, Cookie()] = None) -> Account:
    """Swaps the refresh cookie for a new pair of cookies (the old refresh token stops working)."""
    stored = await security.use_token(refresh_token, "refresh") if refresh_token else None
    user = await User.get(stored.user_id) if stored else None
    if user is None or not user.is_active:
        raise HTTPException(401, "Your session has ended. Log in again.")
    await security.log_in(response, user)
    return _account(user)


@router.post("/logout", status_code=204)
async def logout(response: Response, refresh_token: Annotated[str | None, Cookie()] = None):
    if refresh_token:
        await security.use_token(refresh_token, "refresh")
    security.clear_cookies(response)


@router.get("/me")
async def me(user: CurrentUser) -> Account:
    return _account(user)


# --- Password reset ---

def _send_reset_email(email: str, link: str):
    """Sends the link by SMTP when GPA_TRACKER_SMTP_HOST is set; otherwise writes it to the server log."""
    host = os.getenv("GPA_TRACKER_SMTP_HOST")
    if not host:
        log.warning("Password reset link for %s (no SMTP configured): %s", email, link)
        return
    message = EmailMessage()
    message["From"] = os.getenv("GPA_TRACKER_MAIL_FROM", "cgpa-tracker@localhost")
    message["To"] = email
    message["Subject"] = "Reset your CGPA Tracker password"
    message.set_content(f"Open this link within an hour to choose a new password:\n\n{link}\n\n"
                        "If you did not ask for this, ignore this email.")
    with smtplib.SMTP(host, int(os.getenv("GPA_TRACKER_SMTP_PORT") or 587)) as smtp:
        smtp.starttls()
        if os.getenv("GPA_TRACKER_SMTP_USER"):
            smtp.login(os.environ["GPA_TRACKER_SMTP_USER"], os.environ["GPA_TRACKER_SMTP_PASSWORD"])
        smtp.send_message(message)


class ForgotPassword(BaseModel):
    email: Email


@router.post("/forgot-password", status_code=202, dependencies=LimitedAttempts)
async def forgot_password(body: ForgotPassword, background: BackgroundTasks):
    """Always answers the same way, so it cannot be used to find out who has an account."""
    user = await User.find_one(User.email == body.email)
    if user and user.is_active:
        token = await security.issue_token(user, "password_reset", security.RESET_LIFETIME)
        background.add_task(_send_reset_email, user.email, f"{APP_URL}/reset-password?token={token}")


class ResetPassword(BaseModel):
    token: str
    password: Password


@router.post("/reset-password", status_code=204, dependencies=LimitedAttempts)
async def reset_password(body: ResetPassword):
    stored = await security.use_token(body.token, "password_reset")
    user = await User.get(stored.user_id) if stored else None
    if user is None:
        raise HTTPException(400, "This reset link has expired or was already used. Ask for a new one from the log-in page.")
    user.password_hash = security.hash_password(body.password)
    await user.save()
    await security.revoke_refresh_tokens(user.id)  # log out every other session


# --- Account management ---

def _check_password(user: User, password: str):
    if not security.password_matches(user, password):
        raise HTTPException(403, "The current password is wrong")


class PasswordChange(BaseModel):
    current_password: str
    new_password: Password


@router.put("/password", dependencies=LimitedAttempts)
async def change_password(body: PasswordChange, user: CurrentUser, response: Response) -> Account:
    _check_password(user, body.current_password)
    user.password_hash = security.hash_password(body.new_password)
    await user.save()
    await security.revoke_refresh_tokens(user.id)
    await security.log_in(response, user)  # this browser stays logged in
    return _account(user)


class EmailChange(BaseModel):
    email: Email
    password: str


@router.put("/email", dependencies=LimitedAttempts)
async def change_email(body: EmailChange, user: CurrentUser) -> Account:
    _check_password(user, body.password)
    user.email = body.email
    await user.save()  # a taken email fails on the unique index -> 409
    return _account(user)


class AccountDeletion(BaseModel):
    password: str


@router.post("/delete-account", status_code=204, dependencies=LimitedAttempts)
async def delete_account(body: AccountDeletion, user: CurrentUser, response: Response):
    """Deletes the account and everything it owns. Shared reference data is untouched."""
    _check_password(user, body.password)
    async with transaction() as session:
        for model in ALL_DOCUMENTS:
            if "user_id" in model.model_fields:
                await model.find({"user_id": user.id}, session=session).delete(session=session)
        await user.delete(session=session)
    security.clear_cookies(response)
