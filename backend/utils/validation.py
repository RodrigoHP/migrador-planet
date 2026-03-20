"""Shared validation utilities for job IDs and path safety.

Centralises UUID v4 validation and path traversal prevention, replacing the
private ``_validate_job_id`` functions that were duplicated across routers.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import HTTPException

# Strict UUID v4 pattern — prevents path traversal via jobId
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

TMP_BASE = Path(os.environ.get("JOBS_DIR", "/tmp/jobs"))


def validate_job_id(job_id: str, tmp_base: Path = TMP_BASE) -> str:
    """Validate that *job_id* is a strict UUID v4 string.

    Also verifies that the resolved path for the job directory stays within
    *tmp_base*, preventing path-traversal attacks (e.g., ``../etc/passwd``
    injected as a job_id).

    Args:
        job_id: The raw job identifier string received from the client.
        tmp_base: The base directory that all job directories must reside in.
            Defaults to the value of the ``JOBS_DIR`` environment variable or
            ``/tmp/jobs``.

    Returns:
        The original *job_id* string (unchanged) if valid.

    Raises:
        HTTPException(400): If *job_id* is not a UUID v4 or if the resolved
            path escapes *tmp_base*.
    """
    if not _UUID_RE.match(job_id.lower()):
        raise HTTPException(
            status_code=400,
            detail="jobId inválido: deve ser um UUID v4.",
        )
    # Canonicalize and verify the path stays within tmp_base
    resolved = (tmp_base / job_id).resolve()
    if not str(resolved).startswith(str(tmp_base.resolve())):
        raise HTTPException(
            status_code=400,
            detail="jobId inválido: path fora do escopo permitido.",
        )
    return job_id
