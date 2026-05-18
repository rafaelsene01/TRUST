"""Handles HALT conditions in the TRUST framework.

When any phase fails its Definition of Done in strict mode,
the framework must:
  1. Stop immediately
  2. Preserve all artifacts for investigation
  3. Create a .trust-halt marker file
  4. Print a clear, actionable error message
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import PhaseRecord, PhaseStatus, RunManifest


class HaltError(Exception):
    """Raised when a DoD failure triggers a HALT in strict mode.

    Catching this exception should only happen at the top-level
    orchestrator — never inside individual phase handlers.
    """

    def __init__(
        self,
        phase_id: int,
        phase_name: str,
        blocker: str,
        run_dir: Path,
    ) -> None:
        self.phase_id = phase_id
        self.phase_name = phase_name
        self.blocker = blocker
        self.run_dir = run_dir
        super().__init__(
            f"HALT triggered at phase {phase_id} ({phase_name}): {blocker}"
        )


def record_halt(
    manifest: RunManifest,
    phase: PhaseRecord,
    blocker: str,
    run_dir: Path,
) -> None:
    """Update the manifest and phase record with HALT information."""
    now = datetime.now(tz=timezone.utc).isoformat()
    phase.status = PhaseStatus.HALTED
    phase.dod_passed = False
    phase.blocker = blocker
    phase.ended_at = now
    manifest.overall_status = "halted"
    manifest.blocker = blocker
    manifest.ended_at = now


def write_halt_marker(run_dir: Path, blocker: str) -> Path:
    """Create a .trust-halt marker file in the run directory.

    This file is the signal for other tools (/trust doctor, /trust cleanup)
    that this run needs human attention.
    """
    marker = run_dir / ".trust-halt"
    marker.write_text(
        json.dumps(
            {
                "halted_at": datetime.now(tz=timezone.utc).isoformat(),
                "blocker": blocker,
                "instructions": [
                    "Inspect the run artifacts in this directory",
                    "Fix the reported issue",
                    "Run /trust cleanup <run-id> to remove this marker",
                    "Re-run /trust review-pr to retry",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return marker


def print_halt_message(
    phase_id: int,
    phase_name: str,
    blocker: str,
    run_dir: Path,
    errors: list[str] | None = None,
) -> None:
    """Print a clear, actionable HALT message to stdout."""
    separator = "─" * 60
    print(f"\n{separator}")
    print(f"❌ TRUST HALT — Phase {phase_id}: {phase_name}")
    print(separator)
    print(f"\nBlocker: {blocker}\n")

    if errors:
        print("Details:")
        for err in errors:
            print(f"  • {err}")
        print()

    print(f"Artifacts preserved at:\n  {run_dir}\n")
    print("Next steps:")
    print("  1. Inspect the artifacts listed above")
    print("  2. Fix the reported issue")
    print(f"  3. /trust cleanup {run_dir.name}")
    print("  4. /trust review-pr  (retry)")
    print(f"{separator}\n")


def trigger_halt(
    manifest: RunManifest,
    phase: PhaseRecord,
    blocker: str,
    run_dir: Path,
    errors: list[str] | None = None,
) -> None:
    """Full HALT sequence: record + write marker + print message + raise.

    This is the single entry point for triggering a HALT. Always call
    this instead of raising HaltError directly.
    """
    record_halt(manifest, phase, blocker, run_dir)
    write_halt_marker(run_dir, blocker)
    print_halt_message(phase.phase_id, phase.name, blocker, run_dir, errors)
    raise HaltError(phase.phase_id, phase.name, blocker, run_dir)
