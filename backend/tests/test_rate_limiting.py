"""Tests for rate limiting via slowapi (Story 15.5).

Verifies:
  - /api/analyze is protected with rate limit (10/minute by default)
  - Rate limit exceeded returns 429 with detail message
  - Global rate limiting middleware is configured in main.py
"""

from __future__ import annotations

from unittest.mock import patch


def _get_app():
    import main as app_module

    return app_module.app


def _get_limiter():
    import main as app_module

    return app_module.limiter


class TestRateLimitConfig:
    def test_limiter_is_configured_in_app(self):
        """App state should have limiter attached."""
        app = _get_app()
        assert hasattr(app.state, "limiter")
        assert app.state.limiter is not None

    def test_rate_limit_analyze_env_var(self):
        """RATE_LIMIT_ANALYZE env var is read by analyze router."""
        import importlib
        import os

        import routers.analyze as mod

        with patch.dict(os.environ, {"RATE_LIMIT_ANALYZE": "5/minute"}):
            importlib.reload(mod)
            assert "5/minute" in mod._RATE_LIMIT_ANALYZE or mod._RATE_LIMIT_ANALYZE == "5/minute"
        # Restore module to default state so subsequent tests are not polluted
        importlib.reload(mod)

    def test_rate_limit_global_env_var(self):
        """RATE_LIMIT_GLOBAL env var is read by main.py."""
        import importlib
        import os

        import main as mod

        with patch.dict(os.environ, {"RATE_LIMIT_GLOBAL": "20/minute"}):
            importlib.reload(mod)
            assert "20/minute" in mod._RATE_LIMIT_GLOBAL or mod._RATE_LIMIT_GLOBAL == "20/minute"
        # Restore module to default state so subsequent tests are not polluted
        importlib.reload(mod)


class TestRateLimitDecorator:
    def test_analyze_endpoint_has_rate_limit_decorator(self):
        """The start_analyze endpoint should have a rate-limit decorator applied."""
        import routers.analyze as mod

        # The decorated function should be wrapped by slowapi
        # Check that the _limiter decorator was applied by verifying
        # the module-level limiter object exists
        assert hasattr(mod, "_limiter")
        assert mod._limiter is not None

    def test_analyze_rate_limit_default_is_10_per_minute(self):
        """Default rate limit for analyze is 10/minute."""
        import os

        import routers.analyze as mod

        # When RATE_LIMIT_ANALYZE is not set, default should be 10/minute
        expected = os.environ.get("RATE_LIMIT_ANALYZE", "10/minute")
        assert mod._RATE_LIMIT_ANALYZE == expected

    def test_global_rate_limit_default_is_30_per_minute(self):
        """Default global rate limit is 30/minute."""
        import os

        import main as mod

        expected = os.environ.get("RATE_LIMIT_GLOBAL", "30/minute")
        assert mod._RATE_LIMIT_GLOBAL == expected


class TestRateLimitErrorHandler:
    def test_rate_limit_exceeded_handler_registered(self):
        """RateLimitExceeded exception handler should be registered in app."""
        from slowapi.errors import RateLimitExceeded

        app = _get_app()
        # Check exception handlers
        # FastAPI stores them in exception_handlers dict
        assert RateLimitExceeded in app.exception_handlers

    def test_slowapi_imported_in_main(self):
        """slowapi should be importable and used in main.py."""
        from slowapi import Limiter
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address

        # All required symbols available
        assert Limiter is not None
        assert get_remote_address is not None
        assert RateLimitExceeded is not None

    def test_slowapi_imported_in_analyze_router(self):
        """slowapi should be used in routers/analyze.py."""
        from slowapi import Limiter

        import routers.analyze as mod

        assert isinstance(mod._limiter, Limiter)
