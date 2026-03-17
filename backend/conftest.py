"""pytest configuration — adds vendor directory to sys.path.

Ensures that vendored dependencies (openai, httpx, etc.) are importable
during tests without requiring a separate virtual environment or pip install.
"""

import os
import sys

# Add the vendor directory to sys.path so vendored packages are importable.
_vendor_dir = os.path.join(os.path.dirname(__file__), "vendor")
if _vendor_dir not in sys.path:
    sys.path.insert(0, _vendor_dir)
