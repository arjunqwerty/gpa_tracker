"""Universities, programmes, curricula, course types and grading schemes."""
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import transaction
from app.models import Course, CourseType, CurriculumVersion, GradingScheme, Programme, University
from app.models.common import Code, Name
from app.models.configuration import CourseTemplate, CreditCategory, GradingSchemeFields
from app.ownership import CurrentUser, get_owned, get_visible, visible_to

router = APIRouter(prefix="/api", tags=["configuration"])


# --- Universities and programmes (shared reference data) ---

@router.get("/universities")
async def list_universities() -> list[University]:
    return await University.find_all().to_list()


@router.get("/programmes")
async def list_programmes() -> list[Programme]:
    return await Programme.find_all().to_list()


class ProgrammeIn(BaseModel):
    university_id: PydanticObjectId
    name: str
    degree_type: str
    duration_semesters: int = Field(ge=1)


@router.post("/programmes", status_code=201)
async def create_programme(body: ProgrammeIn) -> Programme:
    if await University.get(body.university_id) is None:
        raise HTTPException(404, "University not found")
    return await Programme(**body.model_dump()).insert()


# --- Curricula: credit requirements per category + course templates ---

class CurriculumIn(BaseModel):
    programme_id: PydanticObjectId | None = None
    version_name: Name
    effective_year: int | None = None
    categories: list[CreditCategory] = []
    course_templates: list[CourseTemplate] = []


@router.get("/curricula")
async def list_curricula(user: CurrentUser) -> list[CurriculumVersion]:
    return await CurriculumVersion.find(visible_to(user)).to_list()


@router.get("/curricula/{curriculum_id}")
async def get_curriculum(curriculum_id: PydanticObjectId, user: CurrentUser) -> CurriculumVersion:
    return await get_visible(CurriculumVersion, curriculum_id, user)


@router.post("/curricula", status_code=201)
async def create_curriculum(body: CurriculumIn, user: CurrentUser) -> CurriculumVersion:
    return await CurriculumVersion(user_id=user.id, **body.model_dump()).insert()


@router.post("/curricula/{curriculum_id}/copy", status_code=201)
async def copy_curriculum(curriculum_id: PydanticObjectId, user: CurrentUser) -> CurriculumVersion:
    """Shared curricula are read-only; copy one to customise it."""
    source = await get_visible(CurriculumVersion, curriculum_id, user)
    fields = CurriculumIn(**source.model_dump()).model_dump()
    fields["version_name"] = f"{source.version_name} (my copy)"
    return await CurriculumVersion(user_id=user.id, **fields).insert()


@router.put("/curricula/{curriculum_id}")
async def update_curriculum(curriculum_id: PydanticObjectId, body: CurriculumIn, user: CurrentUser) -> CurriculumVersion:
    curriculum = await get_owned(CurriculumVersion, curriculum_id, user)
    for field, value in body:
        setattr(curriculum, field, value)
    return await curriculum.save()


# --- Course types ---

class CourseTypeIn(BaseModel):
    code: Code
    name: Name


@router.get("/course-types")
async def list_course_types(user: CurrentUser) -> list[CourseType]:
    return await CourseType.find(visible_to(user)).sort("code").to_list()


@router.post("/course-types", status_code=201)
async def create_course_type(body: CourseTypeIn, user: CurrentUser) -> CourseType:
    return await CourseType(user_id=user.id, **body.model_dump()).insert()


# --- Grading schemes (versioned) ---

@router.get("/grading-schemes")
async def list_grading_schemes(user: CurrentUser, include_archived: bool = False) -> list[GradingScheme]:
    query = {"user_id": user.id} if include_archived else {"user_id": user.id, "is_archived": False}
    return await GradingScheme.find(query).sort("name", "-version").to_list()


@router.post("/grading-schemes", status_code=201)
async def create_grading_scheme(body: GradingSchemeFields, user: CurrentUser) -> GradingScheme:
    return await GradingScheme(user_id=user.id, scheme_key=str(PydanticObjectId()), **body.model_dump()).insert()


@router.put("/grading-schemes/{scheme_id}")
async def update_grading_scheme(scheme_id: PydanticObjectId, body: GradingSchemeFields, user: CurrentUser) -> GradingScheme:
    """Saves a new version. Courses still in progress move to it; recorded results keep the old one."""
    old = await get_owned(GradingScheme, scheme_id, user)
    if old.is_archived:
        raise HTTPException(409, "This is an older version of the grading scheme. Reload the page and edit the latest version.")

    new = GradingScheme(user_id=user.id, scheme_key=old.scheme_key, version=old.version + 1, **body.model_dump())
    async with transaction() as session:
        old.is_archived = True
        await old.save(session=session)
        await new.insert(session=session)
        await Course.find({"user_id": user.id, "grading_scheme_id": old.id, "official_result": None}, session=session).update(
            {"$set": {"grading_scheme_id": new.id}}, session=session
        )
        if user.settings.default_grading_scheme_id == old.id:
            user.settings.default_grading_scheme_id = new.id
            await user.save(session=session)
    return new
