"""SupabaseStorageGateway -- production implementation using Supabase Storage + DB.

Uploads go to the ``jobs`` bucket.  Downloads are cached locally so that tools
like PyMuPDF (which need a real filesystem path) work without re-downloading.

CARDINAL RULE: if Supabase is configured and an operation fails, the error
propagates -- there is NO silent fallback to local storage.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from .gateway import StorageGateway

logger = logging.getLogger(__name__)


class SupabaseStorageGateway(StorageGateway):
    """Implementation backed by Supabase Storage + DB."""

    def __init__(self, supabase: Any, tmp_base: Path | None = None) -> None:
        """Initialise with a Supabase client (sync or async).

        Parameters
        ----------
        supabase: A ``supabase.Client`` or ``supabase.AsyncClient`` instance.
        tmp_base: Local directory for cached downloads (default ``/tmp/jobs``).
        """
        self._supabase = supabase
        self._tmp_base = tmp_base or Path("/tmp/jobs")

    # ------------------------------------------------------------------
    # Upload helpers
    # ------------------------------------------------------------------

    async def upload_pdf(self, job_id: str, index: int, content: bytes) -> str:
        filename = "input.pdf" if index == 0 else f"input_{index + 1}.pdf"
        path = f"jobs/{job_id}/pdfs/{filename}"
        await self._supabase.storage.from_("jobs").upload(path, content)

        # Also save locally for immediate processing (PyMuPDF needs Path)
        local_dir = self._tmp_base / job_id
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / filename).write_bytes(content)

        return path

    async def upload_screenshot(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        path = f"jobs/{job_id}/screenshots/{page_key}.png"
        await self._supabase.storage.from_("jobs").upload(
            path, png_bytes, file_options={"content-type": "image/png"}
        )
        return path

    async def upload_thumbnail(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        path = f"jobs/{job_id}/thumbnails/{page_key}.png"
        await self._supabase.storage.from_("jobs").upload(
            path, png_bytes, file_options={"content-type": "image/png"}
        )
        return path

    async def upload_asset(self, job_id: str, filename: str, content: bytes) -> str:
        path = f"jobs/{job_id}/assets/{filename}"
        await self._supabase.storage.from_("jobs").upload(path, content)
        return path

    # ------------------------------------------------------------------
    # Download / local access
    # ------------------------------------------------------------------

    async def get_local_path(self, job_id: str, filename: str) -> Path:
        local_path = self._tmp_base / job_id / filename
        if local_path.exists():
            return local_path  # cache hit

        # Download from Supabase Storage
        local_path.parent.mkdir(parents=True, exist_ok=True)
        data = await self._supabase.storage.from_("jobs").download(
            f"jobs/{job_id}/pdfs/{filename}"
        )
        local_path.write_bytes(data)
        return local_path

    async def get_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        result = await self._supabase.storage.from_(bucket).create_signed_url(
            path, expires_in
        )
        return result["signedURL"]

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------

    async def save_result(self, job_id: str, result_json: dict) -> None:
        await (
            self._supabase.table("jobs")
            .update({"result_json": result_json, "status": "completed"})
            .eq("id", job_id)
            .execute()
        )

    async def save_clusters(self, job_id: str, clusters: list[dict]) -> None:
        rows = [
            {
                "job_id": job_id,
                "cluster_id": c["cluster_id"],
                "pages": c["pages"],
                "representative": c["representative_page"],
                "confidence": c.get("confidence"),
            }
            for c in clusters
        ]
        await self._supabase.table("job_clusters").upsert(rows).execute()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cleanup_local(self, job_id: str) -> None:
        local_dir = self._tmp_base / job_id
        if local_dir.exists():
            shutil.rmtree(local_dir, ignore_errors=True)

    async def delete_job(self, job_id: str) -> None:
        # Remove files from Supabase Storage
        try:
            files = await self._supabase.storage.from_("jobs").list(f"jobs/{job_id}")
            if files:
                paths = [f["name"] for f in files]
                await self._supabase.storage.from_("jobs").remove(paths)
        except Exception:
            logger.warning("Failed to list/remove storage files for job %s", job_id)
            raise

        # Remove DB rows (cascade will delete job_clusters)
        await self._supabase.table("jobs").delete().eq("id", job_id).execute()

        # Clean local cache
        await self.cleanup_local(job_id)
