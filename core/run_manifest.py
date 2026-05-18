"""Manages the run-manifest.json lifecycle.

The manifest is the single source of truth for a review run's state.
It is written to disk after every phase transition so that a HALT
leaves a fully inspectable state.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .models import PhaseRecord, PhaseStatus, RunManifest


def _generate_run_id(branch: str) -> str:
    """Generate a unique run ID: timestamp + sanitised branch slug."""
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d-%H%M")
    slug = re.sub(r"[^a-z0-9-]", "-", branch.lower())[:30].strip("-")
    return f"{ts}-{slug}"


def _diff_sha(diff_text: str) -> str:
    return hashlib.sha256(diff_text.encode("utf-8")).hexdigest()[:12]


PHASE_DEFINITIONS = [
    (0, "trigger"),
    (1, "grounding"),
    (2, "specialists"),
    (3, "second_pass"),
    (4, "precision_gate"),
    (5, "meta_review"),
    (6, "traceability"),
    (7, "output"),
]


def create_manifest(
    branch: str,
    target_id: str,
    diff_text: str,
    runs_dir: Path,
) -> tuple[RunManifest, Path]:
    """Create a new RunManifest and its on-disk directory.

    Returns:
        (manifest, run_dir) — the manifest object and the path to its directory.
    """
    run_id = _generate_run_id(branch)
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = RunManifest(
        run_id=run_id,
        branch=branch,
        target_id=target_id,
        diff_sha=_diff_sha(diff_text),
        started_at=datetime.now(tz=timezone.utc).isoformat(),
        phases=[
            PhaseRecord(phase_id=pid, name=name)
            for pid, name in PHASE_DEFINITIONS
        ],
    )

    save_manifest(manifest, run_dir)
    return manifest, run_dir


def save_manifest(manifest: RunManifest, run_dir: Path) -> None:
    """Persist the current manifest state to disk."""
    path = run_dir / "run-manifest.json"
    data = {
        "run_id": manifest.run_id,
        "branch": manifest.branch,
        "target_id": manifest.target_id,
        "diff_sha": manifest.diff_sha,
        "started_at": manifest.started_at,
        "ended_at": manifest.ended_at,
        "overall_status": manifest.overall_status,
        "blocker": manifest.blocker,
        "phases": [
            {
                "phase_id": p.phase_id,
                "name": p.name,
                "status": p.status.value,
                "started_at": p.started_at,
                "ended_at": p.ended_at,
                "dod_passed": p.dod_passed,
                "blocker": p.blocker,
                "artifact": p.artifact,
            }
            for p in manifest.phases
        ],
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def mark_phase_start(
    manifest: RunManifest,
    phase_id: int,
    run_dir: Path,
) -> PhaseRecord:
    """Mark a phase as running and persist."""
    phase = manifest.get_phase(phase_id)
    if phase is None:
        raise ValueError(f"Phase {phase_id} not found in manifest.")
    phase.status = PhaseStatus.RUNNING
    phase.started_at = datetime.now(tz=timezone.utc).isoformat()
    save_manifest(manifest, run_dir)
    return phase


def mark_phase_done(
    manifest: RunManifest,
    phase: PhaseRecord,
    run_dir: Path,
    artifact: str | None = None,
) -> None:
    """Mark a phase as successfully done and persist."""
    phase.status = PhaseStatus.DONE
    phase.dod_passed = True
    phase.ended_at = datetime.now(tz=timezone.utc).isoformat()
    phase.artifact = artifact
    save_manifest(manifest, run_dir)


def mark_phase_skipped(
    manifest: RunManifest,
    phase: PhaseRecord,
    run_dir: Path,
    reason: str,
) -> None:
    """Mark a phase as skipped (e.g. traceability disabled) and persist."""
    phase.status = PhaseStatus.SKIPPED
    phase.dod_passed = True   # skip counts as pass for the orchestrator
    phase.blocker = f"skipped: {reason}"
    phase.ended_at = datetime.now(tz=timezone.utc).isoformat()
    save_manifest(manifest, run_dir)


def finalise_manifest(
    manifest: RunManifest,
    run_dir: Path,
) -> None:
    """Mark the overall run as passed and set ended_at."""
    from datetime import datetime, timezone
    manifest.overall_status = "passed"
    manifest.ended_at = datetime.now(tz=timezone.utc).isoformat()
    save_manifest(manifest, run_dir)
