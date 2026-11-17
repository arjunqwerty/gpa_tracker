"""Excel import: upload -> preview & validation -> commit."""
from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response

from app.models import ImportJob
from app.ownership import CurrentUser, get_owned
from app.services import excel_import, exports

router = APIRouter(prefix="/api/import", tags=["import"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@router.get("/template.xlsx")
async def import_template():
    """A blank workbook with every recognised sheet and column."""
    return Response(exports.workbook([], [], None), media_type=XLSX,
                    headers={"Content-Disposition": 'attachment; filename="import-template.xlsx"'})


@router.post("", status_code=201)
async def upload(file: UploadFile, user: CurrentUser) -> ImportJob:
    """Reads and validates the workbook. Nothing is saved until the job is committed."""
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "The file is larger than 5 MB")
    return await excel_import.preview(user, file.filename or "upload.xlsx", content)


@router.get("/{job_id}")
async def get_job(job_id: PydanticObjectId, user: CurrentUser) -> ImportJob:
    return await get_owned(ImportJob, job_id, user)


@router.post("/{job_id}/commit")
async def commit(job_id: PydanticObjectId, user: CurrentUser) -> ImportJob:
    job = await get_owned(ImportJob, job_id, user)
    if job.status != "validated":
        raise HTTPException(409, "This file has errors, so nothing was imported. Fix them in the file and upload it again."
                            if job.status == "failed" else "This file has already been imported.")
    await excel_import.commit(job, user)
    return job
