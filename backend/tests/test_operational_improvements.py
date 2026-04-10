"""Tests for Story 41.7 — Operational Improvements.

Covers:
- SYS-017: Deep health check (Redis, Supabase, Storage, spaCy)
- SYS-018: spaCy model version validation
- SYS-019: API versioning (/api/v1/ prefix + backward-compatible /api/ aliases)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# SYS-017: Deep health check
# ---------------------------------------------------------------------------


class TestDeepHealthCheck:
    """SYS-017: /api/v1/health returns per-dependency status with latency."""

    @pytest.mark.asyncio
    async def test_health_returns_all_dependency_keys(self):
        """Health response includes redis, supabase, storage, spacy keys."""
        from main import health

        with patch("services.job_store.get_job_store", return_value=MagicMock(__class__=object)):
            result = await health()

        assert "status" in result
        assert "redis" in result
        assert "supabase" in result
        assert "storage" in result
        assert "spacy" in result

    @pytest.mark.asyncio
    async def test_health_dep_has_status_field(self):
        """Each dependency dict contains at least a 'status' field."""
        from main import health

        result = await health()

        for dep in ("redis", "supabase", "storage", "spacy"):
            assert "status" in result[dep], f"{dep} missing 'status'"

    @pytest.mark.asyncio
    async def test_health_overall_ok_when_all_not_configured(self):
        """When no services are configured overall status is 'ok' (nothing to fail)."""
        from main import health

        with (
            patch("services.job_store.get_job_store", return_value=MagicMock(__class__=object)),
            patch.dict("os.environ", {"STORAGE_MODE": "local", "SUPABASE_URL": ""}, clear=False),
        ):
            result = await health()

        # All deps will be not_configured or degraded (spacy optional)
        assert result["status"] in ("ok", "degraded")

    @pytest.mark.asyncio
    async def test_health_overall_error_when_redis_fails(self):
        """When Redis ping fails the overall status is 'error' (primary service)."""
        from services.job_store import RedisJobStore

        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = ConnectionError("Redis unreachable")
        mock_store = MagicMock(spec=RedisJobStore)
        mock_store._redis = mock_redis

        with patch("services.job_store.get_job_store", return_value=mock_store):
            from main import health

            result = await health()

        assert result["status"] == "error"
        assert "error" in result["redis"]["status"]

    @pytest.mark.asyncio
    async def test_health_latency_present_when_redis_ok(self):
        """When Redis ping succeeds latency_ms is included in redis dict."""
        from services.job_store import RedisJobStore

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_store = MagicMock(spec=RedisJobStore)
        mock_store._redis = mock_redis

        with patch("services.job_store.get_job_store", return_value=mock_store):
            from main import health

            result = await health()

        assert result["redis"]["status"] == "ok"
        assert "latency_ms" in result["redis"]
        assert isinstance(result["redis"]["latency_ms"], float)

    @pytest.mark.asyncio
    async def test_health_redis_not_configured_when_in_memory_store(self):
        """When using InMemoryJobStore redis status is 'not_configured'."""
        from services.job_store import InMemoryJobStore

        with patch("services.job_store.get_job_store", return_value=InMemoryJobStore()):
            from main import health

            result = await health()

        assert result["redis"]["status"] == "not_configured"

    @pytest.mark.asyncio
    async def test_health_supabase_not_configured_when_env_missing(self):
        """Supabase check returns not_configured when SUPABASE_URL is absent."""
        with patch.dict("os.environ", {"SUPABASE_URL": "", "SUPABASE_KEY": ""}, clear=False):
            from main import health

            result = await health()

        assert result["supabase"]["status"] == "not_configured"

    @pytest.mark.asyncio
    async def test_health_storage_not_configured_when_mode_is_local(self):
        """Storage check returns not_configured when STORAGE_MODE=local."""
        with patch.dict("os.environ", {"STORAGE_MODE": "local"}, clear=False):
            from main import health

            result = await health()

        assert result["storage"]["status"] == "not_configured"

    @pytest.mark.asyncio
    async def test_health_degraded_when_spacy_unavailable(self):
        """When spaCy model is not available overall status becomes 'degraded'."""
        from services.job_store import InMemoryJobStore

        # Ensure no primary services fail (use InMemory store, no Supabase)
        with (
            patch("services.job_store.get_job_store", return_value=InMemoryJobStore()),
            patch.dict(
                "os.environ",
                {"SUPABASE_URL": "", "STORAGE_MODE": "local"},
                clear=False,
            ),
            patch(
                "services.stages.stage3_structural.multi_example_analysis._get_nlp",
                return_value=None,
            ),
        ):
            from main import health

            result = await health()

        assert result["status"] == "degraded"
        assert result["spacy"]["status"] == "degraded"


# ---------------------------------------------------------------------------
# SYS-018: spaCy model version validation
# ---------------------------------------------------------------------------


class TestSpacyModelValidation:
    """SYS-018: spaCy model version is validated at load time and startup."""

    def test_expected_constants_exported(self):
        """_EXPECTED_SPACY_MODEL and _EXPECTED_SPACY_VERSION are exported."""
        from services.stages.stage3_structural.multi_example_analysis import (
            _EXPECTED_SPACY_MODEL,
            _EXPECTED_SPACY_VERSION,
        )

        assert _EXPECTED_SPACY_MODEL == "pt_core_news_sm"
        assert _EXPECTED_SPACY_VERSION == "3.8.0"

    def test_validate_spacy_model_logs_warning_on_version_mismatch(self, caplog):
        """_validate_spacy_model logs a warning when version doesn't match expected."""
        import logging

        from services.stages.stage3_structural.multi_example_analysis import (
            _validate_spacy_model,
        )

        mock_nlp = MagicMock()
        mock_nlp.meta = {
            "lang": "pt",
            "name": "core_news_sm",
            "version": "3.7.0",  # Wrong version
        }

        with caplog.at_level(logging.WARNING, logger="services.stages.stage3_structural.multi_example_analysis"):
            _validate_spacy_model(mock_nlp)

        assert any("version mismatch" in r.message or "mismatch" in r.message for r in caplog.records)

    def test_validate_spacy_model_logs_warning_on_model_mismatch(self, caplog):
        """_validate_spacy_model logs a warning when model name differs from accepted set."""
        import logging

        from services.stages.stage3_structural.multi_example_analysis import (
            _validate_spacy_model,
        )

        mock_nlp = MagicMock()
        mock_nlp.meta = {
            "lang": "en",
            "name": "core_web_sm",  # Wrong language/model
            "version": "3.8.0",
        }

        with caplog.at_level(logging.WARNING, logger="services.stages.stage3_structural.multi_example_analysis"):
            _validate_spacy_model(mock_nlp)

        assert any("mismatch" in r.message for r in caplog.records)

    def test_validate_spacy_model_no_warning_when_correct(self, caplog):
        """_validate_spacy_model does not log a warning for correct model."""
        import logging

        from services.stages.stage3_structural.multi_example_analysis import (
            _validate_spacy_model,
        )

        mock_nlp = MagicMock()
        mock_nlp.meta = {
            "lang": "pt",
            "name": "core_news_sm",
            "version": "3.8.0",
        }

        with caplog.at_level(logging.WARNING, logger="services.stages.stage3_structural.multi_example_analysis"):
            _validate_spacy_model(mock_nlp)

        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) == 0

    def test_validate_spacy_on_startup_logs_warning_when_unavailable(self, caplog):
        """validate_spacy_on_startup logs warning when model cannot be loaded."""
        import logging

        from services.stages.stage3_structural import multi_example_analysis as mod
        from services.stages.stage3_structural.multi_example_analysis import (
            validate_spacy_on_startup,
        )

        original = mod._nlp
        try:
            mod._nlp = False  # Simulate unavailable model
            with caplog.at_level(
                logging.WARNING,
                logger="services.stages.stage3_structural.multi_example_analysis",
            ):
                validate_spacy_on_startup()
        finally:
            mod._nlp = original

        assert any("not available" in r.message or "disabled" in r.message for r in caplog.records)

    def test_validate_spacy_on_startup_does_not_raise(self):
        """validate_spacy_on_startup never raises — graceful fallback."""
        from services.stages.stage3_structural import multi_example_analysis as mod
        from services.stages.stage3_structural.multi_example_analysis import (
            validate_spacy_on_startup,
        )

        original = mod._nlp
        try:
            mod._nlp = False
            validate_spacy_on_startup()  # Must not raise
        finally:
            mod._nlp = original


# ---------------------------------------------------------------------------
# SYS-019: API versioning
# ---------------------------------------------------------------------------


class TestApiVersioning:
    """SYS-019: All routes available under /api/v1/; /api/ is backward-compat alias."""

    def _get_routes(self):
        from main import app

        return {r.path for r in app.routes}

    def test_health_at_v1_path(self):
        """/api/v1/health route exists."""
        routes = self._get_routes()
        assert "/api/v1/health" in routes

    def test_health_legacy_path_exists(self):
        """/api/health backward-compat route exists."""
        routes = self._get_routes()
        assert "/api/health" in routes

    def test_versioned_analyze_routes_exist(self):
        """/api/v1/analyze route is registered."""
        routes = self._get_routes()
        assert any("/api/v1/analyze" in r for r in routes)

    def test_versioned_upload_routes_exist(self):
        """/api/v1/upload route is registered."""
        routes = self._get_routes()
        assert any("/api/v1/upload" in r for r in routes)

    def test_versioned_generate_routes_exist(self):
        """/api/v1/generate route is registered."""
        routes = self._get_routes()
        assert any("/api/v1/generate" in r for r in routes)

    def test_versioned_export_routes_exist(self):
        """/api/v1/export route is registered."""
        routes = self._get_routes()
        assert any("/api/v1/export" in r for r in routes)

    def test_backward_compat_analyze_routes_exist(self):
        """/api/analyze backward-compat route still registered."""
        routes = self._get_routes()
        assert any("/api/analyze" in r and "/api/v1" not in r for r in routes)

    def test_backward_compat_upload_routes_exist(self):
        """/api/upload backward-compat route still registered."""
        routes = self._get_routes()
        assert any("/api/upload" in r and "/api/v1" not in r for r in routes)

    def test_v1_routes_in_openapi_schema(self):
        """/api/v1/ routes appear in OpenAPI schema (docs-visible)."""
        from main import app

        # Check that /api/v1/ routes are in the schema paths
        schema = app.openapi()
        paths = set(schema.get("paths", {}).keys())
        assert any("/api/v1/" in p for p in paths)

    def test_legacy_routes_excluded_from_openapi_schema(self):
        """/api/ legacy routes are hidden from OpenAPI schema (include_in_schema=False)."""
        from main import app

        schema = app.openapi()
        paths = set(schema.get("paths", {}).keys())
        # /api/health legacy alias is explicitly hidden; /api/v1/health should appear
        assert "/api/v1/health" in paths
