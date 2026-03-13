import asyncio
import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from services import job_manager

router = APIRouter()


@router.get("/progress/{job_id}")
async def progress(job_id: str):
    """SSE endpoint: streams job progress events until done or error.

    Handles the race condition where a client connects after the job has
    already completed: immediately emits the terminal event and closes.
    """
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    async def event_generator():
        # Race-condition fix: if job already finished, respond immediately
        current_job = job_manager.get_job(job_id)
        if current_job and current_job.status == "done":
            yield {"event": "done", "data": json.dumps({})}
            return
        if current_job and current_job.status == "error":
            yield {
                "event": "error",
                "data": json.dumps({"message": current_job.error_msg or "Erro desconhecido"}),
            }
            return

        q = job_manager.subscribe(job_id)
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=300)
                except asyncio.TimeoutError:
                    yield {
                        "event": "error",
                        "data": json.dumps({"message": "Timeout aguardando progresso"}),
                    }
                    break
                yield {"event": msg["event"], "data": json.dumps(msg["data"])}
                if msg["event"] in ("done", "error"):
                    break
        finally:
            job_manager.unsubscribe(job_id, q)

    return EventSourceResponse(event_generator())
