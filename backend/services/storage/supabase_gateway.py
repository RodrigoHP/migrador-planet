"""SupabaseStorageGateway -- production implementation using Supabase Storage + DB.

Uploads go to the ``jobs`` bucket.  Downloads are cached locally so that tools
like PyMuPDF (which need a real filesystem path) work without re-downloading.

CARDINAL RULE: if Supabase is configured and an operation fails, the error
propagates -- there is NO silent fallback to local storage.

NOTE: The supabase-py v2 client is synchronous. All storage/db calls are sync
even though the gateway methods are async (for interface compatibility).
"""

from __future__ import annotations

import base64
import json as _json
import logging
import mimetypes
import shutil
from pathlib import Path
from typing import Any

from .gateway import StorageGateway

logger = logging.getLogger(__name__)


class SupabaseStorageGateway(StorageGateway):
    """Implementation backed by Supabase Storage + DB."""

    def __init__(self, supabase: Any, tmp_base: Path | None = None) -> None:
        self._supabase = supabase
        self._tmp_base = tmp_base or Path("/tmp/jobs")

    # ------------------------------------------------------------------
    # Upload helpers
    # ------------------------------------------------------------------

    async def upload_pdf(self, job_id: str, index: int, content: bytes) -> str:
        filename = "input.pdf" if index == 0 else f"input_{index + 1}.pdf"
        path = f"jobs/{job_id}/pdfs/{filename}"
        self._supabase.storage.from_("jobs").upload(path, content)

        # Also save locally for immediate processing (PyMuPDF needs Path)
        local_dir = self._tmp_base / job_id
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / filename).write_bytes(content)

        return path

    async def upload_screenshot(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        path = f"jobs/{job_id}/screenshots/{page_key}.png"
        self._supabase.storage.from_("jobs").upload(
            path, png_bytes, file_options={"content-type": "image/png"}
        )
        return path

    async def upload_thumbnail(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        path = f"jobs/{job_id}/thumbnails/{page_key}.png"
        self._supabase.storage.from_("jobs").upload(
            path, png_bytes, file_options={"content-type": "image/png"}
        )
        return path

    async def upload_asset(self, job_id: str, filename: str, content: bytes) -> str:
        path = f"jobs/{job_id}/assets/{filename}"
        self._supabase.storage.from_("jobs").upload(path, content)
        # For images, return data URI so HTML is self-contained (browser-accessible)
        ext = Path(filename).suffix.lower()
        _IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
        if ext in _IMAGE_EXTS:
            mime = mimetypes.types_map.get(ext, "image/png")
            b64 = base64.b64encode(content).decode("ascii")
            return f"data:{mime};base64,{b64}"
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
        data = self._supabase.storage.from_("jobs").download(
            f"jobs/{job_id}/pdfs/{filename}"
        )
        local_path.write_bytes(data)
        return local_path

    async def get_asset_local_path(self, job_id: str, asset_filename: str) -> Path:
        local_path = self._tmp_base / job_id / "assets" / asset_filename
        if local_path.exists():
            return local_path  # cache hit

        # Download from Supabase Storage — assets live under assets/ in the bucket
        try:
            data = self._supabase.storage.from_("jobs").download(
                f"jobs/{job_id}/assets/{asset_filename}"
            )
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(data)
        except Exception:
            # Asset was not uploaded — caller checks path.exists()
            pass
        return local_path

    async def get_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        result = self._supabase.storage.from_(bucket).create_signed_url(
            path, expires_in
        )
        return result["signedURL"]

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------

    async def save_result(self, job_id: str, result_json: dict) -> None:
        (
            self._supabase.table("jobs")
            .upsert({"id": job_id, "result_json": result_json, "status": "completed"})
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
        self._supabase.table("job_clusters").upsert(rows).execute()

    # ------------------------------------------------------------------
    # Visual data (auxiliary — stored in bucket, not DB)
    # ------------------------------------------------------------------

    async def save_visual_data(self, job_id: str, data: dict) -> None:
        path = f"jobs/{job_id}/visual_data.json"
        content = _json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._supabase.storage.from_("jobs").upload(
            path, content, file_options={"content-type": "application/json"}
        )

    async def load_visual_data(self, job_id: str) -> dict | None:
        path = f"jobs/{job_id}/visual_data.json"
        try:
            raw = self._supabase.storage.from_("jobs").download(path)
            return _json.loads(raw)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cleanup_local(self, job_id: str) -> None:
        local_dir = self._tmp_base / job_id
        if local_dir.exists():
            shutil.rmtree(local_dir, ignore_errors=True)

    async def delete_job(self, job_id: str) -> None:
        try:
            files = self._supabase.storage.from_("jobs").list(f"jobs/{job_id}")
            if files:
                paths = [f["name"] for f in files]
                self._supabase.storage.from_("jobs").remove(paths)
        except Exception:
            logger.warning("Failed to list/remove storage files for job %s", job_id)
            raise

        self._supabase.table("jobs").delete().eq("id", job_id).execute()
        await self.cleanup_local(job_id)
