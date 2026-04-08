import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from services import job_manager
from utils.validation import validate_job_id

router = APIRouter()

TMP_BASE = Path("/tmp/jobs")


@router.get("/export/{job_id}/zip")
async def export_zip(job_id: str):
    """Package generated artifacts as a self-contained ZIP file (FR20)."""
    validate_job_id(job_id)

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
        zf.writestr("template/index.html", html)
        zf.writestr("template/css/style.css", css)
        zf.writestr("template/js/base.js", js)
        zf.writestr("template/js/exemplo.js", exemplo)
        # Story 31.2: assets/ placeholder (actual images added by frontend)
        zf.writestr("template/assets/.gitkeep", "")
    buffer.seek(0)

    return Response(
        content=buffer.read(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="template-{job_id}.zip"'
        },
    )
