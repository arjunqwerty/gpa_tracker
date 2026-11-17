"""VIT reference data (from seed_vit.json) and the starting setup of a new account.

seed_database() runs on every start of the API and only creates what is missing. To seed
without starting the API:  python -m app.seed
"""
import asyncio
import json
from pathlib import Path

from beanie import PydanticObjectId

from app.models import CourseType, CurriculumVersion, GradingScheme, Programme, University, User
from app.models.configuration import CourseTemplate
from app.models.user import Profile

SEED = json.loads(Path(__file__).with_name("seed_vit.json").read_text())


async def _find_or_insert(model, query: dict, **extra_fields):
    return await model.find_one(query) or await model(**query, **extra_fields).insert()



def _vit_course_templates() -> list[CourseTemplate]:
    assessments_by_type = SEED["default_assessments_by_course_type"]
    return [
        CourseTemplate(**template, default_assessments=assessments_by_type.get(template["course_type_code"], []))
        for template in SEED["curriculum"]["course_templates"]
    ]


async def seed_database():
    university = await _find_or_insert(University, SEED["university"])
    programme = await _find_or_insert(Programme, {"university_id": university.id, **SEED["programme"]})

    curriculum_seed = SEED["curriculum"]
    await _find_or_insert(
        CurriculumVersion,
        {"user_id": None, "programme_id": programme.id, "version_name": curriculum_seed["version_name"]},
        effective_year=curriculum_seed["effective_year"],
        categories=curriculum_seed["categories"],
        course_templates=_vit_course_templates(),
    )

    for course_type in SEED["course_types"]:
        await _find_or_insert(CourseType, {"user_id": None, **course_type})


async def create_account(email: str, password_hash: str, full_name: str) -> User:
    """A new user starts on the VIT curriculum with their own editable copy of the VIT grading scheme."""
    curriculum = await CurriculumVersion.find_one({"user_id": None, "version_name": SEED["curriculum"]["version_name"]})
    programme = await Programme.get(curriculum.programme_id)
    user = await User(email=email, password_hash=password_hash, profile=Profile(
        full_name=full_name, university_id=programme.university_id, programme_id=programme.id,
        curriculum_version_id=curriculum.id,
    )).insert()
    scheme = await GradingScheme(user_id=user.id, scheme_key=str(PydanticObjectId()), **SEED["grading_scheme"]).insert()
    user.settings.default_grading_scheme_id = scheme.id
    return await user.save()


async def _seed_from_command_line():
    from app import database
    await database.connect()
    await seed_database()
    print(f"Seeded the VIT reference data into '{database.DATABASE_NAME}'.")
    await database.disconnect()


if __name__ == "__main__":
    asyncio.run(_seed_from_command_line())
