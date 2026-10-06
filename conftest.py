"""Root pytest configuration: make track packages and the service importable."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for p in (ROOT, ROOT / "tracks" / "track-a" / "src", ROOT / "tracks" / "track-b" / "src", ROOT / "service"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def pytest_configure(config):
    config.addinivalue_line("markers", "live: calls a real model API (excluded in CI)")
