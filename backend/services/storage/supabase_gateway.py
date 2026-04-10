"""SupabaseStorageGateway -- production implementation using Supabase Storage + DB.

Uploads go to the ``jobs`` bucket.  Downloads are cached locally so that tools
like PyMuPDF (which need a real filesystem path) work without re-downloading.

CARDINAL RULE: if Supabase is configured and an operation fails, the error
propagates -- there is NO silent fallback to local storage.

Story 40.8 (DB-007): All Supabase SDK calls are wrapped with asyncio.to_thread()
so they don't block the event loop. The supabase-py v2 client is synchronous.

Story 40.8 (DB-017): save_result() checks current job status before writing --
will NOT overwrite cancelled/failed status to completed.

DB-003 (Story 40.2): Two Supabase clients:
  - admin_client (service role) -- ONLY for storage operations (upload, download,
    signed URLs, bucket operations). Bypasses RLS.
  - user_client (anon key + JWT) -- for all DB table queries. Respects RLS.
    Falls back to admin_client when user_client is not configured.

DB-002 (Story 40.2): All DB INSERT/UPDATE operations include user_id from JWT.
"""

from __future__ import annotations

import asyncio
import base64
import json as _json
import logging
import mimetypes
import shutil
from pathlib import Path
from typing import Any

from .gateway import StorageGateway

logger = logging.getLogger(__name__)

# Terminal statuses that must not be overwritten (DB-017 mitigation)
_TERMINAL_STATUSES = frozenset({"cancelled", "failed"})


class SupabaseStorageGateway(StorageGateway):
    """Implementation backed by Supabase Storage + DB.

    DB-003: Uses separate clients for storage (admin) and DB queries (user).
    DB-007: All sync SDK calls wrapped with asyncio.to_thread().
    """

    def __init__(
        self,
        admin_client: Any | None = None,
        user_client: Any | None = None,
        tmp_base: Path | None = None,
        # Legacy compatibility: accept `supabase` kwarg and treat as admin_client
        supabase: Any | None = None,
    ) -> None:
        # Support legacy single-client construction
        if supabase is not None and admin_client is None:
            admin_client = supabase

        if admin_client is None:
            msg = "Either admin_client or supabase must be provided"
            raise ValueError(msg)

        self._admin = admin_client
        # DB-003: user_client for RLS-respecting queries; falls back to admin
        self._user = user_client or admin_client
        self._tmp_base = tmp_base or Path("/tmp/jobs")

        # JWT token for user context (set via set_auth_token)
        self._auth_token: str | None = None
        # User ID extracted from JWT (set via set_user_id)
        self._user_id: str | None = None

    def set_auth_context(self, *, user_id: str, token: str | None = None) -> None:
        """Set the current user context for DB operations.

        DB-002: user_id is included in all INSERT/UPSERT operations.

        Parameters
        ----------
        user_id: The authenticated user's UUID (from JWT 'sub' claim).
        token:   The raw JWT token (for user_client auth header).
        """
        self._user_id = user_id
        self._auth_token = token
        if token and self._user != self._admin:
            # Set the JWT on the user client so RLS sees the correct user
            try:
                self._user.auth.set_session(token, "")
            except Exception:
                # Some supabase-py versions don't support set_session this way;
                # the postgrest headers approach is the fallback
                try:
                    self._user.postgrest.auth(token)
                except Exception:
                    logger.debug("Could not set JWT on user client -- RLS will use anon role")

    def _db_client(self) -> Any:
        """Return the client to use for DB table operations (DB-003)."""
        return self._user

    # ------------------------------------------------------------------
    # Upload helpers (use admin_client -- storage ops bypass RLS)
    # DB-007: All sync SDK calls wrapped with asyncio.to_thread()
    # ------------------------------------------------------------------

    async def upload_pdf(self, job_id: str, index: int, content: bytes) -> str:
        filename = "input.pdf" if index == 0 else f"input_{index + 1}.pdf"
        path = f"jobs/{job_id}/pdfs/{filename}"
        await asyncio.to_thread(self._admin.storage.from_("jobs").upload, path, content)

        # Also save locally for immediate processing (PyMuPDF needs Path)
        local_dir = self._tmp_base / job_id
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / filename).write_bytes(content)

        return path

    async def upload_screenshot(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        path = f"jobs/{job_id}/screenshots/{page_key}.png"
        await asyncio.to_thread(
            self._admin.storage.from_("jobs").upload,
            path,
            png_bytes,
            {"content-type": "image/png"},
        )
        return path

    async def upload_thumbnail(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        path = f"jobs/{job_id}/thumbnails/{page_key}.png"
        await asyncio.to_thread(
            self._admin.storage.from_("jobs").upload,
            path,
            png_bytes,
            {"content-type": "image/png"},
        )
        return path

    async def upload_asset(self, job_id: str, filename: str, content: bytes) -> str:
        path = f"jobs/{job_id}/assets/{filename}"
        await asyncio.to_thread(self._admin.storage.from_("jobs").upload, path, content)
        # For images, return data URI so HTML is self-contained (browser-accessible)
        ext = Path(filename).suffix.lower()
        image_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
        if ext in image_exts:
            mime = mimetypes.types_map.get(ext, "image/png")
            b64 = base64.b64encode(content).decode("ascii")
            return f"data:{mime};base64,{b64}"
        return path

    # ------------------------------------------------------------------
    # Download / local access (use admin_client -- storage ops)
    # DB-007: All sync SDK calls wrapped with asyncio.to_thread()
    # ------------------------------------------------------------------

    async def get_local_path(self, job_id: str, filename: str) -> Path:
        local_path = self._tmp_base / job_id / filename
        if local_path.exists():
            return local_path  # cache hit

        # Download from Supabase Storage (admin client for storage access)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        data = await asyncio.to_thread(
            self._admin.storage.from_("jobs").download,
            f"jobs/{job_id}/pdfs/{filename}",
        )
        local_path.write_bytes(data)
        return local_path

    async def get_asset_local_path(self, job_id: str, asset_filename: str) -> Path:
        local_path = self._tmp_base / job_id / "assets" / asset_filename
        if local_path.exists():
            return local_path  # cache hit

        # Download from Supabase Storage -- assets live under assets/ in the bucket
        try:
            data = await asyncio.to_thread(
                self._admin.storage.from_("jobs").download,
                f"jobs/{job_id}/assets/{asset_filename}",
            )
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(data)
        except Exception:
            # Asset was not uploaded -- caller checks path.exists()
            pass
        return local_path

    async def get_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        result = await asyncio.to_thread(
            self._admin.storage.from_(bucket).create_signed_url,
            path,
            expires_in,
        )
        return result["signedURL"]

    # ------------------------------------------------------------------
    # DB persistence (use user_client -- respects RLS)
    # DB-007: All sync SDK calls wrapped with asyncio.to_thread()
    # DB-017: save_result() guards against overwriting terminal statuses
    # ------------------------------------------------------------------

    async def save_result(self, job_id: str, result_json: dict) -> None:
        # DB-017: Check current status before overwriting
        try:
            current = await asyncio.to_thread(
                lambda: self._db_client().table("jobs").select("status").eq("id", job_id).execute()
            )
            if current.data:
                current_status = current.data[0].get("status")
                if current_status in _TERMINAL_STATUSES:
                    logger.warning(
                        "Blocked save_result for job %s: current status is %s (DB-017 guard)",
                        job_id,
                        current_status,
                    )
                    return
        except Exception:  # noqa: BLE001
            # If we can't check status, proceed with the save (best effort)
            pass

        row: dict[str, Any] = {
            "id": job_id,
            "result_json": result_json,
            "status": "completed",
        }
        # DB-002: Include user_id if available
        if self._user_id:
            row["user_id"] = self._user_id
        await asyncio.to_thread(lambda: self._db_client().table("jobs").upsert(row).execute())

    async def save_clusters(self, job_id: str, clusters: list[dict]) -> None:
        rows = [
            {
                "job_id": job_id,
                "cluster_id": c["cluster_id"],
                "pages": c["pages"],
                "representative": c["representative_page"],
                "confidence": c.get("confidence"),
                # DB-002: Include user_id if available
                **({"user_id": self._user_id} if self._user_id else {}),
            }
            for c in clusters
        ]
        await asyncio.to_thread(lambda: self._db_client().table("job_clusters").upsert(rows).execute())

    # ------------------------------------------------------------------
    # Visual data (auxiliary -- stored in bucket via admin_client)
    # DB-007: All sync SDK calls wrapped with asyncio.to_thread()
    # ------------------------------------------------------------------

    async def save_visual_data(self, job_id: str, data: dict) -> None:
        path = f"jobs/{job_id}/visual_data.json"
        content = _json.dumps(data, ensure_ascii=False).encode("utf-8")
        await asyncio.to_thread(
            self._admin.storage.from_("jobs").upload,
            path,
            content,
            {"content-type": "application/json"},
        )

    async def load_visual_data(self, job_id: str) -> dict | None:
        path = f"jobs/{job_id}/visual_data.json"
        try:
            raw = await asyncio.to_thread(self._admin.storage.from_("jobs").download, path)
            return _json.loads(raw)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Cleanup (admin_client for storage, user_client for DB)
    # DB-007: All sync SDK calls wrapped with asyncio.to_thread()
    # ------------------------------------------------------------------

    async def cleanup_local(self, job_id: str) -> None:
        local_dir = self._tmp_base / job_id
        if local_dir.exists():
            shutil.rmtree(local_dir, ignore_errors=True)

    async def delete_job(self, job_id: str) -> None:
        try:
            files = await asyncio.to_thread(
                self._admin.storage.from_("jobs").list,
                f"jobs/{job_id}",
            )
            if files:
                paths = [f["name"] for f in files]
                await asyncio.to_thread(self._admin.storage.from_("jobs").remove, paths)
        except Exception:
            logger.warning("Failed to list/remove storage files for job %s", job_id)
            raise

        await asyncio.to_thread(lambda: self._db_client().table("jobs").delete().eq("id", job_id).execute())
        await self.cleanup_local(job_id)
