import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

router = APIRouter()

TMP_BASE = Path("/tmp/jobs")

# Strict UUID v4 pattern — prevents path traversal via jobId
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def _validate_job_id(job_id: str) -> str:
    """Validate that job_id is a strict UUID v4 string.

    Raises HTTP 400 if the value does not match to prevent path traversal attacks.
    """
    if not _UUID_RE.match(job_id.lower()):
        raise HTTPException(status_code=400, detail="jobId inválido: deve ser um UUID v4.")
    # Canonicalization: ensure resolved path is under TMP_BASE
    resolved = (TMP_BASE / job_id).resolve()
    if not str(resolved).startswith(str(TMP_BASE.resolve())):
        raise HTTPException(status_code=400, detail="jobId inválido: path fora do escopo permitido.")
    return job_id


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
    _validate_job_id(job_id)
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
    _validate_job_id(jobId)
    job_dir = get_job_dir(jobId)
    content = await file.read()
    (job_dir / "schema.xsd").write_bytes(content)
    return {"jobId": jobId}


@router.post("/upload/data")
async def upload_data(
    file: UploadFile = File(...),
    jobId: str = Form(...),
):
    _validate_job_id(jobId)
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
