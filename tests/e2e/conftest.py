"""Pytest fixtures for TRUST E2E tests.

Shared fixtures used by test_mvp.py, which was originally designed for
standalone execution. These fixtures reconstruct the same setup that
test_mvp.main() builds.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
MOCK_GROUNDING = FIXTURES_DIR / "mock-grounding"
MOCK_DIFF = FIXTURES_DIR / "mock-diff" / "feat-PAY-123.patch"
CHECKLIST = REPO_ROOT / "templates" / "checklists" / "security.checklist.md"


@pytest.fixture(scope="session")
def tmp_dir(tmp_path_factory) -> Path:
    """Session-scoped temp dir shared by all MVP tests."""
    return tmp_path_factory.mktemp("trust_e2e")


@pytest.fixture(scope="session")
def setup_path(tmp_dir: Path) -> Path:
    """Build a minimal setup repo once per session."""
    # Import here to avoid circular issues at collection time
    from tests.e2e.test_mvp import build_mock_setup
    return build_mock_setup(tmp_dir)


@pytest.fixture(scope="session")
def run_dir(tmp_dir: Path, setup_path: Path) -> Path:
    """Create a run dir, populate with mock findings, and run pipeline phases."""
    from core.run_manifest import create_manifest
    from tests.e2e.test_mvp import make_mock_findings, run_pipeline_phases

    runs_dir = setup_path / "runs"
    manifest, the_run_dir = create_manifest(
        "feat/PAY-123", "mock-product", "mock-diff", runs_dir
    )

    # Copy diff
    shutil.copy(MOCK_DIFF, the_run_dir / "diff.patch")

    # Simulate agent writing findings
    make_mock_findings(the_run_dir)

    # Run pipeline phases 4-7
    run_pipeline_phases(setup_path, the_run_dir)

    return the_run_dir
