from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from services import job_manager

router = APIRouter()

_TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "base_template.html"


class PreviewRequest(BaseModel):
    jobId: str


@router.post("/preview")
async def preview(request: PreviewRequest):
    """Return a fully-rendered HTML page for the given job result."""
    job = job_manager.get_job(request.jobId)
    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job.status in ("pending", "running"):
        raise HTTPException(status_code=409, detail="Job ainda em processamento")
    if job.status == "error":
        raise HTTPException(status_code=422, detail=job.error_msg or "Erro desconhecido")

    result = job.result or {}

    css = result.get("css", "")
    js = result.get("js", "")
    exemplo = result.get("exemplo", "")
    content = result.get("html", "")

    # Inject exampleData script before the ViewModel JS so it is available
    js_combined = f"{exemplo}\n{js}" if exemplo else js

    try:
        base_html = _TEMPLATE_PATH.read_text(encoding="utf-8")
        html_output = (
            base_html
            .replace("{styles}", css)
            .replace("{content}", content)
            .replace("{js}", js_combined)
        )
    except FileNotFoundError:
        # Fallback: inline everything without template file
        html_output = (
            "<!DOCTYPE html>\n"
            '<html lang="pt-BR">\n'
            "<head>\n"
            '  <meta charset="UTF-8">\n'
            f"  <style>{css}</style>\n"
            "</head>\n"
            "<body>\n"
            f'  <div id="form-container" style="position:relative;">{content}</div>\n'
            '  <script src="https://cdnjs.cloudflare.com/ajax/libs/knockout/3.5.1/knockout-min.js"></script>\n'
            f"  <script>{js_combined}</script>\n"
            "</body>\n"
            "</html>"
        )

    return Response(content=html_output, media_type="text/html")
