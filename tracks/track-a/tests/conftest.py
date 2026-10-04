import json
import sys
from pathlib import Path
import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Also add repo root so `from tracks.common.schemas import ...` works
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CASES_ROOT = REPO_ROOT / "tracks" / "cases"


@pytest.fixture
def repo_root() -> Path:
    """Path to repository root."""
    return REPO_ROOT


@pytest.fixture
def cases_root() -> Path:
    """Path to canonical case-pack directory."""
    return CASES_ROOT


@pytest.fixture
def case_index(cases_root: Path) -> list[str]:
    """All registered case slugs from index.json."""
    index_file = cases_root / "index.json"
    return json.loads(index_file.read_text(encoding="utf-8"))["cases"]


@pytest.fixture
def micrometer_bundle(cases_root: Path) -> dict:
    """Canonical micrometer replay bundle."""
    bundle_file = cases_root / "micrometer" / "replay" / "bundle.json"
    return json.loads(bundle_file.read_text(encoding="utf-8"))
