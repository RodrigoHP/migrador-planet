import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services.storage import get_storage
from utils.validation import validate_job_id

router = APIRouter()

# Kept for backward compatibility (get_job_dir used by other modules).
TMP_BASE = Path(os.environ.get("JOBS_DIR", "/tmp/jobs"))


def get_job_dir(job_id: str) -> Path:
    path = TMP_BASE / job_id
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' não encontrado. Faça o upload do PDF primeiro.",
        )
    return path


@router.post("/upload")
async def upload_unified(
    pdfs: list[UploadFile] = File(..., alias="pdfs[]"),
    xsd: UploadFile = File(...),
    template_name: str = Form(""),
    data: UploadFile | None = File(None),
):
    """Unified upload endpoint consumed by the frontend UploadPage."""
    job_id = str(uuid.uuid4())
    validate_job_id(job_id)
    storage = get_storage()

    # Save PDFs via storage gateway
    for index, pdf_file in enumerate(pdfs):
        content = await pdf_file.read()
        await storage.upload_pdf(job_id, index, content)

    # Save XSD via storage gateway
    xsd_content = await xsd.read()
    await storage.upload_asset(job_id, "schema.xsd", xsd_content)

    # Save data file (optional) — detect extension by filename, then by content
    if data is not None:
        data_content = await data.read()
        filename = data.filename or ""
        if filename.endswith(".xml"):
            ext = "xml"
        elif filename.endswith(".json"):
            ext = "json"
        else:
            ext = "xml" if data_content.lstrip().startswith(b"<") else "json"
        await storage.upload_asset(job_id, f"data.{ext}", data_content)

    return {"job_id": str(job_id)}


@router.post("/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    storage = get_storage()
    content = await file.read()
    await storage.upload_pdf(job_id, 0, content)
    return {"jobId": job_id}


@router.post("/upload/xsd")
async def upload_xsd(
    file: UploadFile = File(...),
    jobId: str = Form(...),
):
    validate_job_id(jobId)
    storage = get_storage()
    content = await file.read()
    await storage.upload_asset(jobId, "schema.xsd", content)
    return {"jobId": jobId}


@router.post("/upload/data")
async def upload_data(
    file: UploadFile = File(...),
    jobId: str = Form(...),
):
    validate_job_id(jobId)
    storage = get_storage()
    content = await file.read()

    filename = file.filename or ""
    if filename.endswith(".xml"):
        ext = "xml"
    elif filename.endswith(".json"):
        ext = "json"
    else:
        # fallback: detect by content
        ext = "xml" if content.lstrip().startswith(b"<") else "json"

    await storage.upload_asset(jobId, f"data.{ext}", content)
    return {"jobId": jobId}
