import os
import re
import uuid
from pathlib import Path

import fitz  # PyMuPDF
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services.storage import get_storage
from utils.validation import TMP_BASE, validate_job_id


def sanitize_template_name(name: str) -> str:
    """TD-38.2: Sanitize template_name — strip HTML, limit charset, max 100 chars."""
    # Strip HTML tags
    clean = re.sub(r"<[^>]*>", "", name)
    # Keep only alphanumeric, spaces, hyphens, underscores, dots
    clean = re.sub(r"[^\w\s\-.]", "", clean)
    # Collapse whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    # Max 100 characters
    return clean[:100]


router = APIRouter()

# TMP_BASE imported from utils.validation (single source of truth)

# Upload limits (configurable via env vars)
_MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", "50"))
_MAX_FILE_SIZE_BYTES = _MAX_FILE_SIZE_MB * 1024 * 1024
_MAX_PAGE_COUNT = int(os.environ.get("MAX_PAGE_COUNT", "500"))


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

    # Validate and save PDFs via storage gateway
    total_pages = 0
    for index, pdf_file in enumerate(pdfs):
        content = await pdf_file.read()

        # File size validation
        if len(content) > _MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {_MAX_FILE_SIZE_MB}MB",
            )

        # Page count validation
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            total_pages += len(doc)
            doc.close()
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid PDF file")

        if total_pages > _MAX_PAGE_COUNT:
            raise HTTPException(
                status_code=422,
                detail=f"Too many pages. Maximum: {_MAX_PAGE_COUNT}",
            )

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

    # Story 38.6: Persist template_name as metadata so analyze can propagate it
    # TD-38.2: Sanitize before persisting
    template_name = sanitize_template_name(template_name)
    if template_name:
        await storage.upload_asset(job_id, "template_name.txt", template_name.encode("utf-8"))

    return {"job_id": str(job_id), "template_name": template_name}


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
