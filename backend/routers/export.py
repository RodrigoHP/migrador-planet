import io
import re
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from services import job_manager

router = APIRouter()

TMP_BASE = Path("/tmp/jobs")

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def _validate_job_id(job_id: str) -> str:
    if not _UUID_RE.match(job_id.lower()):
        raise HTTPException(status_code=400, detail="jobId inválido: deve ser um UUID v4.")
    resolved = (TMP_BASE / job_id).resolve()
    if not str(resolved).startswith(str(TMP_BASE.resolve())):
        raise HTTPException(status_code=400, detail="jobId inválido: path fora do escopo permitido.")
    return job_id


@router.get("/export/{job_id}/zip")
async def export_zip(job_id: str):
    """Package generated artifacts as a self-contained ZIP file (FR20)."""
    _validate_job_id(job_id)

    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job.status in ("pending", "running"):
        raise HTTPException(status_code=409, detail="Job ainda em processamento")
    if job.status == "error":
        raise HTTPException(status_code=422, detail=job.error_msg or "Erro desconhecido")

    result = job.result or {}
    html = result.get("html", "<!-- template vazio -->")
    css = result.get("css", "")
    js = result.get("js", "")
    exemplo = result.get("exemplo", "")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html)
        zf.writestr("css/style.css", css)
        zf.writestr("js/base.js", js)
        zf.writestr("exemplo.js", exemplo)
    buffer.seek(0)

    return Response(
        content=buffer.read(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="template-{job_id}.zip"'
        },
    )
