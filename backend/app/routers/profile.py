from fastapi import APIRouter
from pydantic import BaseModel

from app.models import CurriculumVersion, GradingScheme
from app.models.user import Profile, UserSettings
from app.ownership import CurrentUser, get_owned, get_visible

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileData(BaseModel):
    profile: Profile
    settings: UserSettings


@router.get("")
async def get_profile(user: CurrentUser) -> ProfileData:
    return ProfileData(profile=user.profile, settings=user.settings)


@router.put("")
async def update_profile(body: ProfileData, user: CurrentUser) -> ProfileData:
    if body.settings.default_grading_scheme_id:
        await get_owned(GradingScheme, body.settings.default_grading_scheme_id, user)
    if body.profile.curriculum_version_id:
        await get_visible(CurriculumVersion, body.profile.curriculum_version_id, user)
    user.profile, user.settings = body.profile, body.settings
    await user.save()
    return body
