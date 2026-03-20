import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from utils.validation import validate_job_id

router = APIRouter()

TMP_BASE = Path(os.environ.get("JOBS_DIR", "/tmp/jobs"))


def create_job_dir(job_id: str) -> Path:
    path = TMP_BASE / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


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
    job_dir = create_job_dir(job_id)

    # Save PDFs: first as input.pdf, subsequent as input_2.pdf, input_3.pdf …
    for index, pdf_file in enumerate(pdfs):
        content = await pdf_file.read()
        suffix = "" if index == 0 else f"_{index + 1}"
        (job_dir / f"input{suffix}.pdf").write_bytes(content)

    # Save XSD
    xsd_content = await xsd.read()
    (job_dir / "schema.xsd").write_bytes(xsd_content)

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
        (job_dir / f"data.{ext}").write_bytes(data_content)

    return {"job_id": str(job_id)}


@router.post("/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    job_dir = create_job_dir(job_id)
    content = await file.read()
    (job_dir / "input.pdf").write_bytes(content)
    return {"jobId": job_id}


@router.post("/upload/xsd")
async def upload_xsd(
    file: UploadFile = File(...),
    jobId: str = Form(...),
):
    validate_job_id(jobId)
    job_dir = get_job_dir(jobId)
    content = await file.read()
    (job_dir / "schema.xsd").write_bytes(content)
    return {"jobId": jobId}


@router.post("/upload/data")
async def upload_data(
    file: UploadFile = File(...),
    jobId: str = Form(...),
):
    validate_job_id(jobId)
    job_dir = get_job_dir(jobId)
    content = await file.read()

    filename = file.filename or ""
    if filename.endswith(".xml"):
        ext = "xml"
    elif filename.endswith(".json"):
        ext = "json"
    else:
        # fallback: detect by content
        ext = "xml" if content.lstrip().startswith(b"<") else "json"

    (job_dir / f"data.{ext}").write_bytes(content)
    return {"jobId": jobId}
