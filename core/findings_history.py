"""Findings history aggregator for TRUST v2.1 — Learning Loop.

Scans the setup repo's ``runs/`` directory and consolidates all past findings
into per-rule statistics that the rule suggester uses to propose calibrations.

What gets tracked per rule:
  - How many times it fired (total_findings)
  - How many findings were above the confidence threshold (passed)
  - How many were silenced (below threshold)
  - How many were intercepted as hallucinations by Meta-Review
  - Average confidence score
  - Last run that produced a finding from this rule

The data is *objective* (derived from artifacts) — it does not require
reviewer feedback. When developers add reviewer feedback later
(e.g. marking findings as false positives in REVIEW.md), those signals
can be layered on top.

Usage:

    history = build_history(runs_dir)
    for stat in history.rule_stats:
        print(f"{stat.rule_id}: {stat.total_findings} findings, "
              f"{stat.hallucination_rate:.0%} hallucination rate")
    history.export_json(Path("runs/learning/history.json"))
    history.export_markdown(Path("runs/learning/history.md"))
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RuleStat:
    """Aggregated statistics for a single rule across all runs."""

    rule_id: str
    agent: str = ""
    total_findings: int = 0       # all findings (passed + silenced + hallu)
    passed: int = 0               # above threshold, survived meta-review
    silenced: int = 0             # below confidence threshold
    hallucinations: int = 0       # intercepted by meta-review
    confidence_sum: float = 0.0   # for computing average
    last_seen: str = ""           # run_id of last occurrence
    files_affected: set = field(default_factory=set)

    @property
    def avg_confidence(self) -> float:
        return self.confidence_sum / self.total_findings if self.total_findings else 0.0

    @property
    def hallucination_rate(self) -> float:
        total = self.passed + self.hallucinations
        return self.hallucinations / total if total else 0.0

    @property
    def silence_rate(self) -> float:
        return self.silenced / self.total_findings if self.total_findings else 0.0

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "agent": self.agent,
            "total_findings": self.total_findings,
            "passed": self.passed,
            "silenced": self.silenced,
            "hallucinations": self.hallucinations,
            "avg_confidence": round(self.avg_confidence, 3),
            "hallucination_rate": round(self.hallucination_rate, 3),
            "silence_rate": round(self.silence_rate, 3),
            "last_seen": self.last_seen,
            "files_affected": sorted(self.files_affected),
        }


@dataclass
class RunEntry:
    """Summary of a single run's contribution to the history."""

    run_id: str
    branch: str
    target_id: str
    started_at: str
    finding_count: int
    hallucination_count: int
    halted: bool


@dataclass
class FindingsHistory:
    """Consolidated findings history across all runs."""

    runs: list[RunEntry] = field(default_factory=list)
    rule_stats: list[RuleStat] = field(default_factory=list)
    scanned_runs: int = 0
    error_runs: int = 0           # runs whose artifacts couldn't be read
    built_at: str = ""

    @property
    def total_findings(self) -> int:
        return sum(r.finding_count for r in self.runs)

    @property
    def total_hallucinations(self) -> int:
        return sum(r.hallucination_count for r in self.runs)

    @property
    def halt_rate(self) -> float:
        if not self.runs:
            return 0.0
        return sum(1 for r in self.runs if r.halted) / len(self.runs)

    def get_rule(self, rule_id: str) -> RuleStat | None:
        return next((s for s in self.rule_stats if s.rule_id == rule_id), None)

    def sorted_by(self, key: str = "total_findings", descending: bool = True) -> list[RuleStat]:
        return sorted(self.rule_stats, key=lambda s: getattr(s, key, 0), reverse=descending)

    def export_json(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "built_at": self.built_at,
            "scanned_runs": self.scanned_runs,
            "error_runs": self.error_runs,
            "total_findings": self.total_findings,
            "total_hallucinations": self.total_hallucinations,
            "halt_rate": round(self.halt_rate, 3),
            "runs": [
                {
                    "run_id": r.run_id,
                    "branch": r.branch,
                    "target_id": r.target_id,
                    "started_at": r.started_at,
                    "finding_count": r.finding_count,
                    "hallucination_count": r.hallucination_count,
                    "halted": r.halted,
                }
                for r in self.runs
            ],
            "rule_stats": [s.to_dict() for s in self.sorted_by("total_findings")],
        }
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def export_markdown(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# TRUST — Findings History",
            f"\n> Built at: {self.built_at}",
            f"> Runs scanned: {self.scanned_runs} ({self.error_runs} errors)",
            f"> Total findings: {self.total_findings}",
            f"> Hallucination rate: {self.total_hallucinations}/{self.total_findings + self.total_hallucinations}",
            f"> HALT rate: {self.halt_rate:.0%}",
            "\n## Rule Statistics\n",
            "| Rule | Agent | Findings | Passed | Silenced | Hallucinations | Avg Conf | Hallu Rate |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for s in self.sorted_by("total_findings"):
            lines.append(
                f"| `{s.rule_id}` | {s.agent} | {s.total_findings} | {s.passed} | "
                f"{s.silenced} | {s.hallucinations} | {s.avg_confidence:.0%} | "
                f"{s.hallucination_rate:.0%} |"
            )
        output_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Aggregation logic
# ---------------------------------------------------------------------------


def _read_run_artifacts(run_dir: Path) -> tuple[RunEntry | None, list[dict], list[dict]]:
    """Read a single run's artifacts.

    Returns:
        (run_entry, passed_findings, hallucinations) or (None, [], []) on error.
    """
    manifest_file = run_dir / "run-manifest.json"
    gate_file = run_dir / "gate.report.json"
    meta_file = run_dir / "meta-review.json"

    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, [], []

    run_entry = RunEntry(
        run_id=manifest.get("run_id", run_dir.name),
        branch=manifest.get("branch", ""),
        target_id=manifest.get("target_id", ""),
        started_at=manifest.get("started_at", ""),
        finding_count=0,
        hallucination_count=0,
        halted=manifest.get("overall_status") == "halted",
    )

    passed: list[dict] = []
    hallucinations: list[dict] = []

    if gate_file.exists():
        try:
            gate = json.loads(gate_file.read_text(encoding="utf-8"))
            passed = gate.get("passed", [])
            silenced = gate.get("silenced", [])
            run_entry.finding_count = len(passed) + len(silenced)
        except (OSError, json.JSONDecodeError):
            pass

    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            hallucinations = meta.get("hallucinations_caught_detail", [])
            run_entry.hallucination_count = len(hallucinations)
        except (OSError, json.JSONDecodeError):
            pass

    return run_entry, passed, hallucinations


def _update_stats(
    stats: dict[str, RuleStat],
    findings: list[dict],
    run_id: str,
    category: str,  # "passed" | "silenced" | "hallucination"
    gate_silenced: list[dict] | None = None,
) -> None:
    """Accumulate finding stats into the stats dict."""
    for f in findings:
        rule_id = f.get("rule_id", "UNKNOWN")
        agent = rule_id.split("-")[0].lower() if "-" in rule_id else ""

        if rule_id not in stats:
            stats[rule_id] = RuleStat(rule_id=rule_id, agent=agent)

        stat = stats[rule_id]
        stat.total_findings += 1
        stat.confidence_sum += f.get("confidence", 0.0)
        stat.last_seen = run_id
        if f_file := f.get("file"):
            stat.files_affected.add(f_file)

        if category == "passed":
            stat.passed += 1
        elif category == "silenced":
            stat.silenced += 1
        elif category == "hallucination":
            stat.hallucinations += 1


def build_history(
    runs_dir: Path,
    target_filter: str | None = None,
    min_date: str | None = None,
) -> FindingsHistory:
    """Scan runs_dir and build a consolidated FindingsHistory.

    Args:
        runs_dir:      Path to the setup repo's ``runs/`` directory.
        target_filter: If set, only include runs for this target_id.
        min_date:      If set (ISO format YYYY-MM-DD), skip runs before this date.

    Returns:
        FindingsHistory populated from all readable run artifacts.
    """
    history = FindingsHistory(
        built_at=datetime.now(tz=timezone.utc).isoformat()
    )

    if not runs_dir.is_dir():
        return history

    stats: dict[str, RuleStat] = {}

    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        # Skip learning/ subdirectory
        if run_dir.name == "learning":
            continue

        history.scanned_runs += 1

        run_entry, passed, hallucinations = _read_run_artifacts(run_dir)
        if run_entry is None:
            history.error_runs += 1
            continue

        # Apply filters
        if target_filter and run_entry.target_id != target_filter:
            continue
        if min_date and run_entry.started_at and run_entry.started_at[:10] < min_date:
            continue

        history.runs.append(run_entry)

        # Also read silenced from gate report
        gate_file = run_dir / "gate.report.json"
        silenced: list[dict] = []
        if gate_file.exists():
            try:
                gate = json.loads(gate_file.read_text(encoding="utf-8"))
                silenced = gate.get("silenced", [])
            except (OSError, json.JSONDecodeError):
                pass

        _update_stats(stats, passed, run_entry.run_id, "passed")
        _update_stats(stats, silenced, run_entry.run_id, "silenced")
        _update_stats(stats, hallucinations, run_entry.run_id, "hallucination")

    history.rule_stats = list(stats.values())
    return history
