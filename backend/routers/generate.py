import asyncio
import re
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.field_mapping import FieldMapping
from services import job_manager
from services.fidelity_scorer import FidelityScorer
from services.template_generator import TemplateGenerator

router = APIRouter()

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

GENERATION_TIMEOUT_SECONDS = 300


class MonacoEdits(BaseModel):
    html: Optional[str] = None
    css: Optional[str] = None
    js: Optional[str] = None


class GenerateRequest(BaseModel):
    mappingFields: List[dict] = []
    layoutConfig: dict = {}
    monacoEdits: MonacoEdits = MonacoEdits()


@router.post("/generate")
async def start_generate(request: GenerateRequest):
    """Start template generation pipeline and return jobId immediately."""
    job_id = str(uuid.uuid4())
    job_manager.create_job(job_id)
    asyncio.create_task(run_generation_pipeline(job_id, request))
    return {"jobId": job_id}


async def run_generation_pipeline(job_id: str, request: GenerateRequest) -> None:
    try:
        await asyncio.wait_for(
            _generation_inner(job_id, request),
            timeout=GENERATION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        job_manager.set_error(job_id, "Timeout: geração excedeu 5 minutos")
        await job_manager.emit(job_id, "error", {"message": "Timeout: geração excedeu 5 minutos"})


async def _generation_inner(job_id: str, request: GenerateRequest) -> None:
    try:
        if job_id in job_manager.jobs:
            job_manager.jobs[job_id].status = "running"

        # Convert dicts to FieldMapping (Pydantic v2)
        fields: List[FieldMapping] = [FieldMapping.model_validate(f) for f in request.mappingFields]

        # Generate template (blocks=[] — positional CSS only)
        gen = TemplateGenerator()
        output = gen.generate(fields, blocks=[])
        await job_manager.emit(job_id, "step", {"step": "Gerando HTML", "pct": 30})

        # Fidelity score
        scorer = FidelityScorer()
        fidelity = scorer.score(fields)
        await job_manager.emit(job_id, "step", {"step": "Calculando fidelidade", "pct": 70})

        # Apply monacoEdits as overrides
        html = request.monacoEdits.html or output["html"]
        css = request.monacoEdits.css or output["css"]
        js = request.monacoEdits.js or output["js"]

        result = {
            "html": html,
            "css": css,
            "js": js,
            "exemplo": output["exemplo"],
            "fidelityScore": fidelity["score"],
            "fidelityComment": fidelity["comment"],
            "iaSuggestions": fidelity["suggestions"],
        }
        job_manager.set_result(job_id, result)
        await job_manager.emit(job_id, "done", {})

    except Exception as exc:
        error_msg = str(exc)
        job_manager.set_error(job_id, error_msg)
        await job_manager.emit(job_id, "error", {"message": error_msg})
