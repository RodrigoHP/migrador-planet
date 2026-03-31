"""StorageGateway ABC -- abstraction for storage operations.

Stages interact with storage exclusively through this interface.
Two implementations exist:
- SupabaseStorageGateway (production: Supabase Storage + DB)
- LocalStorageGateway (dev/tests: local disk)

The active implementation is chosen by the STORAGE_MODE env var via the
factory in __init__.py.  There is NO automatic fallback: if cloud is
configured and fails, the pipeline fails.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class StorageGateway(ABC):
    """Abstraction for storage -- stages don't know if it's disk or cloud."""

    @abstractmethod
    async def upload_pdf(self, job_id: str, index: int, content: bytes) -> str:
        """Persist a PDF and return an identifier (URL or local path).

        Parameters
        ----------
        job_id:  Unique job identifier.
        index:   Zero-based index of the PDF within the job.
        content: Raw PDF bytes.

        Returns
        -------
        str: Storage path or URL that identifies the uploaded file.
        """

    @abstractmethod
    async def upload_screenshot(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        """Persist a page screenshot (150 DPI) and return its URL/path.

        Parameters
        ----------
        job_id:    Unique job identifier.
        page_key:  Page identifier (e.g. ``"page_0"``).
        png_bytes: Raw PNG image bytes.
        """

    @abstractmethod
    async def upload_asset(self, job_id: str, filename: str, content: bytes) -> str:
        """Persist an extracted image asset and return its URL/path.

        Parameters
        ----------
        job_id:   Unique job identifier.
        filename: Asset filename (e.g. ``"img_0_3.png"``).
        content:  Raw image bytes.
        """

    @abstractmethod
    async def upload_thumbnail(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        """Persist a thumbnail for pHash/LLM clustering and return its URL/path.

        Parameters
        ----------
        job_id:    Unique job identifier.
        page_key:  Page identifier.
        png_bytes: Raw PNG image bytes.
        """

    @abstractmethod
    async def get_local_path(self, job_id: str, filename: str) -> Path:
        """Return a local filesystem Path for *filename*.

        For cloud implementations this downloads the file (with local cache).
        PyMuPDF and other tools require a real filesystem path.

        Parameters
        ----------
        job_id:   Unique job identifier.
        filename: File name relative to the job directory.
        """

    @abstractmethod
    async def get_asset_local_path(self, job_id: str, asset_filename: str) -> Path:
        """Return a local filesystem Path for an asset file (e.g. ``schema.xsd``).

        Assets are stored under the ``assets/`` sub-directory of the job.
        For cloud implementations this downloads the file to a local cache so
        that pipeline stages can open it via a regular filesystem path.

        The returned path may not exist if the asset was never uploaded —
        callers must check ``path.exists()`` before using it.

        Parameters
        ----------
        job_id:         Unique job identifier.
        asset_filename: Asset file name only (e.g. ``"schema.xsd"``).
        """

    @abstractmethod
    async def get_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        """Generate a time-limited URL for frontend access.

        Parameters
        ----------
        bucket:     Storage bucket name.
        path:       Object path within the bucket.
        expires_in: URL validity in seconds (default 3600).
        """

    @abstractmethod
    async def save_result(self, job_id: str, result_json: dict) -> None:
        """Persist the pipeline result to the database.

        Parameters
        ----------
        job_id:      Unique job identifier.
        result_json: Canonical result dict produced by the pipeline.
        """

    @abstractmethod
    async def save_clusters(self, job_id: str, clusters: list[dict]) -> None:
        """Persist layout clusters to the database.

        Parameters
        ----------
        job_id:   Unique job identifier.
        clusters: List of cluster dicts with keys ``cluster_id``, ``pages``,
                  ``representative_page``, and optionally ``confidence``.
        """

    @abstractmethod
    async def cleanup_local(self, job_id: str) -> None:
        """Remove temporary local files for a job (after pipeline completion).

        Parameters
        ----------
        job_id: Unique job identifier.
        """

    @abstractmethod
    async def save_visual_data(self, job_id: str, data: dict) -> None:
        """Persist auxiliary visual extraction data (drawn_elements, text_blocks).

        Parameters
        ----------
        job_id: Unique job identifier.
        data:   Dict with structure ``{"pages": [{"page_index": int,
                "cluster_id": str, "drawn_elements": list, "text_blocks": list}]}``.
        """

    @abstractmethod
    async def load_visual_data(self, job_id: str) -> dict | None:
        """Load previously persisted visual extraction data.

        Parameters
        ----------
        job_id: Unique job identifier.

        Returns
        -------
        dict | None: The visual data dict, or ``None`` if not found.
        """

    @abstractmethod
    async def delete_job(self, job_id: str) -> None:
        """Delete all artefacts for a job (Storage files + DB rows).

        Parameters
        ----------
        job_id: Unique job identifier.
        """
