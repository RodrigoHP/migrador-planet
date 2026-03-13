import asyncio
import re
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.extraction_result import ExtractionResult
from services import job_manager
from services.data_parser import DataParser
from services.fidelity_scorer import FidelityScorer
from services.matcher import Matcher
from services.pdf_extractor import PDFExtractor
from services.template_generator import TemplateGenerator
from services.xsd_parser import XSDParser

router = APIRouter()

TMP_BASE = Path("/tmp/jobs")
JOB_TIMEOUT_SECONDS = 300  # 5 minutes (AC7)

# Strict UUID v4 pattern — prevents path traversal via job_id
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def _validate_job_id(job_id: str) -> str:
    """Validate that job_id is a strict UUID v4. Prevents path traversal attacks."""
    if not _UUID_RE.match(job_id.lower()):
        raise HTTPException(status_code=400, detail="jobId inválido: deve ser um UUID v4.")
    resolved = (TMP_BASE / job_id).resolve()
    if not str(resolved).startswith(str(TMP_BASE.resolve())):
        raise HTTPException(status_code=400, detail="jobId inválido: path fora do escopo permitido.")
    return job_id


class StartJobRequest(BaseModel):
    jobId: str


# ---------------------------------------------------------------------------
# Background pipeline
# ---------------------------------------------------------------------------

async def run_pipeline(job_id: str) -> None:
    """Run the full pipeline with a 5-minute timeout (AC7)."""
    try:
        await asyncio.wait_for(_pipeline_inner(job_id), timeout=JOB_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        job_manager.set_error(job_id, "Timeout: pipeline excedeu 5 minutos")
        await job_manager.emit(job_id, "error", {"message": "Timeout: pipeline excedeu 5 minutos"})


async def _pipeline_inner(job_id: str) -> None:
    """Full pipeline: PDF extraction → field matching → template generation."""
    job_dir = TMP_BASE / job_id
    pdf_path = job_dir / "input.pdf"
    xsd_path = job_dir / "schema.xsd"

    # Determine data file (prefer .json, fall back to .xml)
    data_path_json = job_dir / "data.json"
    data_path_xml = job_dir / "data.xml"
    data_path = data_path_json if data_path_json.exists() else (
        data_path_xml if data_path_xml.exists() else None
    )

    try:
        if job_id in job_manager.jobs:
            job_manager.jobs[job_id].status = "running"

        start_time = time.monotonic()

        # --- Phase 1: Extract PDF ---
        extractor = PDFExtractor()
        blocks = extractor.extract(pdf_path)
        # Derive page count from block metadata (TextBlock.page is 1-based)
        pdf_page_count = max((b.page for b in blocks), default=0)
        # Emit AFTER phase completes (pct reflects completion, not intent)
        await job_manager.emit(job_id, "step", {"step": "Extraindo PDF", "pct": 20})

        # --- Phase 2: Field Matching ---
        xsd_fields = []
        data_fields: dict[str, str] = {}

        if xsd_path.exists():
            xsd_parser = XSDParser()
            xsd_fields = xsd_parser.parse(xsd_path)

        if data_path is not None:
            data_parser = DataParser()
            data_fields = data_parser.parse(data_path)

        matcher = Matcher()
        field_mappings = matcher.match(blocks, xsd_fields, data_fields)
        # Emit AFTER matching completes
        await job_manager.emit(job_id, "step", {"step": "Matching de campos", "pct": 60})

        # --- Phase 3: Template Generation ---
        template_gen = TemplateGenerator()
        template_output = template_gen.generate(field_mappings, blocks)

        scorer = FidelityScorer()
        fidelity = scorer.score(field_mappings)

        processing_time = round(time.monotonic() - start_time, 2)
        # Emit AFTER generation completes
        await job_manager.emit(job_id, "step", {"step": "Gerando template", "pct": 85})

        result = ExtractionResult(
            fields=field_mappings,
            pdfPageCount=pdf_page_count,
            xsdFieldCount=len(xsd_fields),
            processingTime=processing_time,
            fidelityScore=fidelity["score"],
            fidelityComment=fidelity["comment"],
            iaSuggestions=fidelity["suggestions"],
            html=template_output["html"],
            css=template_output["css"],
            js=template_output["js"],
            exemplo=template_output["exemplo"],
        )

        job_manager.set_result(job_id, result.model_dump())
        await job_manager.emit(job_id, "done", {})

    except Exception as exc:
        error_msg = str(exc)
        job_manager.set_error(job_id, error_msg)
        await job_manager.emit(job_id, "error", {"message": error_msg})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/jobs")
async def start_job(request: StartJobRequest):
    """Create a job and start the processing pipeline in the background."""
    job_id = _validate_job_id(request.jobId)
    pdf_path = TMP_BASE / job_id / "input.pdf"

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"PDF não encontrado para jobId '{job_id}'. Faça o upload primeiro.",
        )

    job_manager.create_job(job_id)
    asyncio.create_task(run_pipeline(job_id))

    return {"jobId": job_id}


@router.get("/result/{job_id}")
async def get_result(job_id: str):
    """Return the ExtractionResult once the job is done."""
    job = job_manager.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    if job.status in ("pending", "running"):
        raise HTTPException(status_code=409, detail="Job ainda em processamento")

    if job.status == "error":
        raise HTTPException(status_code=422, detail=job.error_msg or "Erro desconhecido")

    return job.result
