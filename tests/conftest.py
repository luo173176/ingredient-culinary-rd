from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture(scope="session")
def skill_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def db_path(skill_root: Path) -> Path:
    return skill_root / "data" / "index" / "knowledge.sqlite"
