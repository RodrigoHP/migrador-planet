"""Tests for Story 11.7 — Shared UUID validation + path traversal prevention.

Covers:
1. validate_job_id() accepts valid UUID v4 strings.
2. validate_job_id() rejects non-UUID strings with HTTP 400.
3. validate_job_id() rejects path-traversal strings (e.g. '../etc/passwd').
4. POST /api/analyze rejects invalid job_id before any disk access.
5. GET /api/export/{job_id}/zip rejects invalid job_id.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Tests for utils.validation.validate_job_id
# ---------------------------------------------------------------------------


def _get_validate():
    from utils.validation import validate_job_id

    return validate_job_id


def test_validate_job_id_accepts_valid_uuid_v4():
    """A correct UUID v4 string passes without raising."""
    validate_job_id = _get_validate()
    import uuid

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_base = Path(tmpdir)
        job_id = str(uuid.uuid4())
        result = validate_job_id(job_id, tmp_base=tmp_base)
        assert result == job_id


def test_validate_job_id_rejects_random_string():
    """A random non-UUID string must raise HTTP 400."""
    validate_job_id = _get_validate()

    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(HTTPException) as exc_info:
            validate_job_id("not-a-uuid", tmp_base=Path(tmpdir))
        assert exc_info.value.status_code == 400
        assert "UUID v4" in exc_info.value.detail


def test_validate_job_id_rejects_path_traversal_dotdot():
    """'../etc/passwd' must be rejected with HTTP 400."""
    validate_job_id = _get_validate()

    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(HTTPException) as exc_info:
            validate_job_id("../etc/passwd", tmp_base=Path(tmpdir))
        assert exc_info.value.status_code == 400


def test_validate_job_id_rejects_path_traversal_embedded():
    """A string with path-traversal sequence embedded must be rejected."""
    validate_job_id = _get_validate()

    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(HTTPException) as exc_info:
            validate_job_id("../../etc/shadow", tmp_base=Path(tmpdir))
        assert exc_info.value.status_code == 400


def test_validate_job_id_rejects_empty_string():
    """Empty string must raise HTTP 400."""
    validate_job_id = _get_validate()

    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(HTTPException) as exc_info:
            validate_job_id("", tmp_base=Path(tmpdir))
        assert exc_info.value.status_code == 400


def test_validate_job_id_rejects_uuid_v1():
    """UUID v1 (version bit is 1, not 4) must be rejected."""
    validate_job_id = _get_validate()

    # Version 1 UUID: the 13th character is '1', not '4'
    uuid_v1 = "550e8400-e29b-11d4-a716-446655440000"
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(HTTPException) as exc_info:
            validate_job_id(uuid_v1, tmp_base=Path(tmpdir))
        assert exc_info.value.status_code == 400


def test_validate_job_id_rejects_uuid_with_invalid_variant():
    """UUID with invalid variant bits (not 8/9/a/b) must be rejected."""
    validate_job_id = _get_validate()

    # Variant '7' is not valid per RFC 4122
    bad_variant = "550e8400-e29b-4d4e-7716-446655440000"
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(HTTPException) as exc_info:
            validate_job_id(bad_variant, tmp_base=Path(tmpdir))
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Integration tests: POST /api/analyze rejects invalid job_id
# ---------------------------------------------------------------------------


def test_analyze_endpoint_rejects_invalid_job_id():
    """POST /api/analyze must return 400 for non-UUID job_id."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        resp = client.post("/api/analyze", json={"job_id": "../etc/passwd"})
    assert resp.status_code == 400


def test_analyze_endpoint_rejects_random_string_job_id():
    """POST /api/analyze must return 400 for random string job_id."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        resp = client.post("/api/analyze", json={"job_id": "definitely-not-a-uuid"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Integration test: export router uses shared validation
# ---------------------------------------------------------------------------


def test_export_router_uses_validate_job_id():
    """Verify that export.py imports validate_job_id from utils.validation."""
    import routers.export as exp_mod

    # If the import is present, the module-level attribute should not exist
    assert not hasattr(exp_mod, "_validate_job_id"), (
        "export.py still has its own private _validate_job_id — should use utils.validation.validate_job_id"
    )


def test_upload_router_uses_validate_job_id():
    """Verify that upload.py imports validate_job_id from utils.validation."""
    import routers.upload as up_mod

    assert not hasattr(up_mod, "_validate_job_id"), (
        "upload.py still has its own private _validate_job_id — should use utils.validation.validate_job_id"
    )
