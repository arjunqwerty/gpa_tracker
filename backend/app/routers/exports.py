"""Downloads: workbook, grade history, credit report, PDF reports and a full JSON backup."""
from beanie import PydanticObjectId
from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response

from app.models import AuditLog, CurriculumVersion, GradingScheme, Semester
from app.models.common import utc_now
from app.ownership import CurrentUser, get_owned
from app.services import calculations, exports

router = APIRouter(prefix="/api/export", tags=["export"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def download(content: bytes, filename: str, media_type: str) -> Response:
    return Response(content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/workbook.xlsx")
async def workbook(user: CurrentUser):
    """All semesters, courses, marks and requirements, in the import layout."""
    record = await calculations.load_record(user, include_withdrawn=True)
    curriculum = await calculations.user_curriculum(user)
    return download(exports.workbook(record.semesters, record.courses, curriculum), "academic-record.xlsx", XLSX)


@router.get("/grade-history.xlsx")
async def grade_history_xlsx(user: CurrentUser):
    record = await calculations.load_record(user)
    rows = exports.grade_history_rows(record.semesters, record.courses)
    return download(exports.xlsx({"Grade history": rows}), "grade-history.xlsx", XLSX)


@router.get("/grade-history.csv")
async def grade_history_csv(user: CurrentUser):
    record = await calculations.load_record(user)
    return download(exports.csv_bytes(*exports.grade_history_rows(record.semesters, record.courses)), "grade-history.csv", "text/csv")


@router.get("/credits.csv")
async def credits_csv(user: CurrentUser):
    record = await calculations.load_record(user)
    report = calculations.credit_report(record, await calculations.user_curriculum(user))
    return download(exports.csv_bytes(*exports.credit_rows(report)), "credit-progress.csv", "text/csv")


@router.get("/summary.pdf")
async def summary_pdf(user: CurrentUser):
    record = await calculations.load_record(user)
    semesters = [calculations.summarise_semester(s, record.courses, record.schemes, user) for s in record.semesters]
    report = calculations.credit_report(record, await calculations.user_curriculum(user))
    pdf = exports.summary_pdf(user.profile.full_name, calculations.cgpa_report(record, user), semesters, report)
    return download(pdf, "academic-summary.pdf", "application/pdf")


@router.get("/semesters/{semester_id}.pdf")
async def semester_pdf(semester_id: PydanticObjectId, user: CurrentUser):
    semester = await get_owned(Semester, semester_id, user)
    record = await calculations.load_record(user)
    summary = calculations.summarise_semester(semester, record.courses, record.schemes, user)
    pdf = exports.summary_pdf(user.profile.full_name, calculations.cgpa_report(record, user), [summary], None)
    return download(pdf, f"{semester.label}.pdf", "application/pdf")


@router.get("/full.json")
async def full_backup(user: CurrentUser):
    """Every document that belongs to the user."""
    record = await calculations.load_record(user, include_withdrawn=True)
    owned = {"user_id": user.id}
    data = {
        "exported_at": utc_now(),
        "profile": user.profile,
        "settings": user.settings,
        "semesters": record.semesters,
        "courses": record.courses,
        "grading_schemes": await GradingScheme.find(owned).to_list(),
        "curricula": await CurriculumVersion.find(owned).to_list(),
        "audit_log": await AuditLog.find(owned).to_list(),
    }
    return JSONResponse(jsonable_encoder(data), headers={"Content-Disposition": 'attachment; filename="gpa-tracker-backup.json"'})
