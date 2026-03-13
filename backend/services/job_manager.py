import asyncio
from typing import Any, Dict, List, Optional

from models.job import Job

jobs: Dict[str, Job] = {}
job_queues: Dict[str, List[asyncio.Queue]] = {}


def create_job(job_id: str) -> Job:
    job = Job(job_id=job_id, status="pending")
    jobs[job_id] = job
    job_queues[job_id] = []
    return job


def get_job(job_id: str) -> Optional[Job]:
    return jobs.get(job_id)


def set_result(job_id: str, result: Any) -> None:
    if job_id in jobs:
        jobs[job_id].status = "done"
        jobs[job_id].result = result


def set_error(job_id: str, msg: str) -> None:
    if job_id in jobs:
        jobs[job_id].status = "error"
        jobs[job_id].error_msg = msg


async def emit(job_id: str, event: str, data: dict) -> None:
    for q in job_queues.get(job_id, []):
        await q.put({"event": event, "data": data})


def subscribe(job_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    job_queues.setdefault(job_id, []).append(q)
    return q


def unsubscribe(job_id: str, q: asyncio.Queue) -> None:
    if job_id in job_queues:
        try:
            job_queues[job_id].remove(q)
        except ValueError:
            pass
