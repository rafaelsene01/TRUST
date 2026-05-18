"""Run lifecycle management — artifact retention and HALT state preservation.

The orchestrator delegates all post-run cleanup to this module so the
lifecycle policy stays in one place and is independently testable.

Retention policies (from trust.config.yaml `retention_policy`):

  all_versioned      — keep every artifact forever (audit trail)
  audit_failures_only — on success: remove JSON artifacts, keep REVIEW.md
                        on HALT:   keep everything (for post-mortem)
  gitignored         — same as audit_failures_only (deprecated alias)
  ephemeral          — delete the entire run dir on success

The HALT state of a run is determined by the presence of a `.trust-halt`
file in the run directory, written by halt_handler.trigger_halt().
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class LifecycleResult:
    """Outcome of running the lifecycle policy on a completed run."""

    run_dir: Path
    policy: str
    halted: bool
    action: str  # "kept_all" | "removed_json" | "removed_run" | "noop"
    removed_files: list[str]
    kept_files: list[str]


def apply_retention(run_dir: Path, retention_policy: str) -> LifecycleResult:
    """Apply the retention policy after a run completes.

    Args:
        run_dir:          The run's working directory (e.g. runs/feat-PAY-123-abc123/)
        retention_policy: One of the four policy strings above.

    Returns:
        LifecycleResult describing what was kept or removed.
    """
    halted = _is_halted(run_dir)

    if retention_policy == "all_versioned":
        return LifecycleResult(
            run_dir=run_dir,
            policy=retention_policy,
            halted=halted,
            action="kept_all",
            removed_files=[],
            kept_files=_list_files(run_dir),
        )

    if retention_policy == "ephemeral":
        if halted:
            # Never delete HALT artifacts — they're the post-mortem record
            return _remove_json_artifacts(run_dir, retention_policy, halted)
        kept = _list_files(run_dir)
        try:
            shutil.rmtree(run_dir, ignore_errors=True)
        except Exception:
            pass
        return LifecycleResult(
            run_dir=run_dir,
            policy=retention_policy,
            halted=halted,
            action="removed_run",
            removed_files=kept,
            kept_files=[],
        )

    if retention_policy in ("audit_failures_only", "gitignored"):
        if halted:
            # HALT → keep everything for post-mortem
            return LifecycleResult(
                run_dir=run_dir,
                policy=retention_policy,
                halted=halted,
                action="kept_all",
                removed_files=[],
                kept_files=_list_files(run_dir),
            )
        # Success → remove JSON artifacts, keep REVIEW.md and manifest
        return _remove_json_artifacts(run_dir, retention_policy, halted)

    # Unknown policy — log and keep everything
    return LifecycleResult(
        run_dir=run_dir,
        policy=retention_policy,
        halted=halted,
        action="kept_all",
        removed_files=[],
        kept_files=_list_files(run_dir),
    )


def is_halted(run_dir: Path) -> bool:
    """Return True if this run ended in a HALT."""
    return _is_halted(run_dir)


def preserve_halt_artifacts(run_dir: Path) -> list[str]:
    """Return the list of files preserved for a HALT post-mortem.

    Does not delete anything — just returns what's there.
    """
    return _list_files(run_dir)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_halted(run_dir: Path) -> bool:
    return (run_dir / ".trust-halt").exists()


def _list_files(directory: Path) -> list[str]:
    """Return relative paths of all files under directory."""
    if not directory.exists():
        return []
    return [
        str(f.relative_to(directory))
        for f in sorted(directory.rglob("*"))
        if f.is_file()
    ]


_KEEP_EXTENSIONS = {".md", ".txt", ".log"}
_KEEP_FILENAMES = {"run.manifest.json", "REVIEW.md", ".trust-halt"}


def _remove_json_artifacts(
    run_dir: Path, policy: str, halted: bool
) -> LifecycleResult:
    """Remove JSON artifacts from a successful run, keeping REVIEW.md and manifest."""
    removed: list[str] = []
    kept: list[str] = []

    if not run_dir.exists():
        return LifecycleResult(
            run_dir=run_dir,
            policy=policy,
            halted=halted,
            action="noop",
            removed_files=[],
            kept_files=[],
        )

    # Remove agent subdirectory JSONs
    agents_dir = run_dir / "agents"
    if agents_dir.exists():
        agent_files = list(agents_dir.rglob("*"))
        for f in agent_files:
            if f.is_file():
                try:
                    removed.append(str(f.relative_to(run_dir)))
                    f.unlink()
                except Exception:
                    kept.append(str(f.relative_to(run_dir)))
        try:
            shutil.rmtree(agents_dir, ignore_errors=True)
        except Exception:
            pass

    # Remove JSON files from run root (except manifest)
    for f in run_dir.glob("*.json"):
        if f.name in _KEEP_FILENAMES:
            kept.append(f.name)
            continue
        try:
            removed.append(f.name)
            f.unlink()
        except Exception:
            kept.append(f.name)

    # Document what's kept
    for f in sorted(run_dir.rglob("*")):
        if f.is_file():
            rel = str(f.relative_to(run_dir))
            if rel not in removed:
                kept.append(rel)

    return LifecycleResult(
        run_dir=run_dir,
        policy=policy,
        halted=halted,
        action="removed_json",
        removed_files=removed,
        kept_files=kept,
    )
