"""LocalStorageGateway -- dev/test implementation using local disk.

Wraps the existing ``/tmp/jobs`` behaviour behind the StorageGateway ABC.
No cloud services are involved; ``get_signed_url`` returns a local API path
so the frontend can fetch files via the backend's static file serving.
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import shutil
from pathlib import Path

from .gateway import StorageGateway

logger = logging.getLogger(__name__)


class LocalStorageGateway(StorageGateway):
    """Implementation backed by local filesystem (dev/test mode)."""

    def __init__(self, tmp_base: Path | None = None) -> None:
        """Initialise with a base directory for job files.

        Parameters
        ----------
        tmp_base: Root directory for job data (default ``/tmp/jobs``).
        """
        self._tmp_base = tmp_base or Path("/tmp/jobs")

    # ------------------------------------------------------------------
    # Uploads (write to local disk)
    # ------------------------------------------------------------------

    async def upload_pdf(self, job_id: str, index: int, content: bytes) -> str:
        filename = "input.pdf" if index == 0 else f"input_{index + 1}.pdf"
        local_dir = self._tmp_base / job_id
        local_dir.mkdir(parents=True, exist_ok=True)
        path = local_dir / filename
        path.write_bytes(content)
        return str(path)

    async def upload_screenshot(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        path = self._tmp_base / job_id / "screenshots" / f"{page_key}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png_bytes)
        return str(path)

    async def upload_thumbnail(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        path = self._tmp_base / job_id / "thumbnails" / f"{page_key}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png_bytes)
        return str(path)

    async def upload_asset(self, job_id: str, filename: str, content: bytes) -> str:
        path = self._tmp_base / job_id / "assets" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        # For image files, return a data URI so HTML templates embed them inline
        # (filesystem paths are not browser-accessible and are cleaned up post-pipeline)
        ext = Path(filename).suffix.lower()
        _IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
        if ext in _IMAGE_EXTS:
            mime = mimetypes.types_map.get(ext, "image/png")
            b64 = base64.b64encode(content).decode("ascii")
            return f"data:{mime};base64,{b64}"
        return str(path)

    # ------------------------------------------------------------------
    # Local access
    # ------------------------------------------------------------------

    async def get_local_path(self, job_id: str, filename: str) -> Path:
        return self._tmp_base / job_id / filename  # already local

    async def get_asset_local_path(self, job_id: str, asset_filename: str) -> Path:
        return self._tmp_base / job_id / "assets" / asset_filename  # already local

    async def get_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        return f"/api/files/{path}"  # served via local API

    # ------------------------------------------------------------------
    # Persistence (JSON files on disk)
    # ------------------------------------------------------------------

    async def save_result(self, job_id: str, result_json: dict) -> None:
        job_dir = self._tmp_base / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        result_path = job_dir / "result.json"
        result_path.write_text(json.dumps(result_json, ensure_ascii=False, indent=2))

    async def save_clusters(self, job_id: str, clusters: list[dict]) -> None:
        job_dir = self._tmp_base / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        clusters_path = job_dir / "clusters.json"
        clusters_path.write_text(json.dumps(clusters, ensure_ascii=False, indent=2))

    # ------------------------------------------------------------------
    # Visual data (auxiliary)
    # ------------------------------------------------------------------

    async def save_visual_data(self, job_id: str, data: dict) -> None:
        job_dir = self._tmp_base / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        path = job_dir / "visual_data.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    async def load_visual_data(self, job_id: str) -> dict | None:
        path = self._tmp_base / job_id / "visual_data.json"
        if not path.exists():
            return None
        return dict(json.loads(path.read_text()))

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cleanup_local(self, job_id: str) -> None:
        local_dir = self._tmp_base / job_id
        if local_dir.exists():
            shutil.rmtree(local_dir, ignore_errors=True)

    async def delete_job(self, job_id: str) -> None:
        # Local mode: deleting the directory is the only cleanup needed
        await self.cleanup_local(job_id)
