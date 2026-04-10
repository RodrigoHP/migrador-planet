"""pytest configuration for backend test suite."""

import os

# Disable authentication for tests (Story 15.3)
os.environ.setdefault("AUTH_DISABLED", "true")
