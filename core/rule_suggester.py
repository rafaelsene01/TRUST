"""Rule suggester for TRUST v2.1 — Learning Loop.

Analyzes findings history and produces three types of suggestions:

    threshold_adjustment
        Rules where the current threshold is too low (lots of hallucinations)
        or too high (lots of silenced findings that look real).

    disable_candidate
        Rules that never fire after many runs, suggesting the rule is either
        irrelevant to this codebase or the grounding doesn't cover the domain.

    enable_candidate
        Rules that consistently produce high-confidence, non-hallucinatory
        findings — a signal to promote them in priority or expand coverage.

    review_manually
        Rules with extreme false-positive signals (high hallucination rate)
        that need human review before any automated action.

Output is a CalibrationReport which can be written to
``runs/learning/YYYY-MM-DD-calibration.json`` and applied with
``/trust learn apply``.

Usage:

    history = build_history(runs_dir)
    report = suggest_calibrations(history, current_threshold=0.80)
    report.export_json(Path("runs/learning/calibration.json"))
    report.print_summary()
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .findings_history import FindingsHistory, RuleStat


# ---------------------------------------------------------------------------
# Thresholds for heuristics (all configurable via SuggesterConfig)
# ---------------------------------------------------------------------------


@dataclass
class SuggesterConfig:
    """Tuning parameters for the suggestion heuristics."""

    min_runs_for_suggestion: int = 5      # don't suggest until there's enough data
    hallucination_rate_high: float = 0.30  # above this → raise threshold or review
    hallucination_rate_low: float = 0.05   # below this → rule is trustworthy
    silence_rate_high: float = 0.60        # mostly silenced → consider lowering threshold
    never_fired_runs: int = 10             # ran N times without a finding → disable candidate
    threshold_step: float = 0.05           # granularity of threshold adjustments


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RuleSuggestion:
    """A single calibration suggestion."""

    suggestion_type: str          # "threshold_adjustment" | "disable_candidate" |
                                  # "enable_candidate" | "review_manually"
    rule_id: str
    rationale: str
    current_threshold: float | None = None
    suggested_threshold: float | None = None
    priority: str = "medium"      # "high" | "medium" | "low"

    def to_dict(self) -> dict:
        d: dict = {
            "suggestion_type": self.suggestion_type,
            "rule_id": self.rule_id,
            "rationale": self.rationale,
            "priority": self.priority,
        }
        if self.current_threshold is not None:
            d["current_threshold"] = self.current_threshold
        if self.suggested_threshold is not None:
            d["suggested_threshold"] = self.suggested_threshold
        return d


@dataclass
class ThresholdAdjustment:
    """Recommended threshold change for a rule."""

    rule_id: str
    current: float
    suggested: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "current": self.current,
            "suggested": self.suggested,
            "reason": self.reason,
        }


@dataclass
class CalibrationReport:
    """Full calibration report produced by the rule suggester."""

    suggestions: list[RuleSuggestion] = field(default_factory=list)
    threshold_adjustments: list[ThresholdAdjustment] = field(default_factory=list)
    analyzed_rules: int = 0
    rules_skipped_insufficient_data: int = 0
    built_at: str = ""
    current_threshold: float = 0.80

    def export_json(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "built_at": self.built_at,
            "current_threshold": self.current_threshold,
            "analyzed_rules": self.analyzed_rules,
            "rules_skipped_insufficient_data": self.rules_skipped_insufficient_data,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "threshold_adjustments": [t.to_dict() for t in self.threshold_adjustments],
        }
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def export_markdown(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# TRUST — Calibration Report",
            f"\n> Built at: {self.built_at}",
            f"> Rules analyzed: {self.analyzed_rules}",
            f"> Rules skipped (insufficient data): {self.rules_skipped_insufficient_data}",
            f"> Current threshold: {self.current_threshold:.0%}",
            "\n## Suggestions\n",
        ]

        if not self.suggestions:
            lines.append("✅ No calibration suggestions — the current configuration looks good.")
        else:
            priority_order = ["high", "medium", "low"]
            for priority in priority_order:
                group = [s for s in self.suggestions if s.priority == priority]
                if not group:
                    continue
                icons = {"high": "🔴", "medium": "🟡", "low": "🔵"}
                lines.append(f"### {icons[priority]} {priority.capitalize()} priority\n")
                for s in group:
                    type_label = s.suggestion_type.replace("_", " ").title()
                    lines.append(f"**[{type_label}]** `{s.rule_id}`")
                    lines.append(f"> {s.rationale}")
                    if s.suggested_threshold is not None:
                        lines.append(
                            f"> Threshold: {s.current_threshold:.0%} → "
                            f"{s.suggested_threshold:.0%}"
                        )
                    lines.append("")

        if self.threshold_adjustments:
            lines += [
                "\n## Threshold Adjustments to Apply\n",
                "| Rule | Current | Suggested | Reason |",
                "| --- | --- | --- | --- |",
            ]
            for t in self.threshold_adjustments:
                lines.append(
                    f"| `{t.rule_id}` | {t.current:.0%} | {t.suggested:.0%} | {t.reason} |"
                )

        output_path.write_text("\n".join(lines), encoding="utf-8")

    def print_summary(self) -> None:
        """Print a concise summary to stdout."""
        print(f"\n📊 Calibration report — {self.built_at[:10]}")
        print(f"   Rules analyzed: {self.analyzed_rules}")
        if not self.suggestions:
            print("   ✅ No suggestions — configuration looks good.")
            return
        high = sum(1 for s in self.suggestions if s.priority == "high")
        med = sum(1 for s in self.suggestions if s.priority == "medium")
        low = sum(1 for s in self.suggestions if s.priority == "low")
        print(f"   Suggestions: {high} high, {med} medium, {low} low")
        for s in self.suggestions:
            icon = {"high": "🔴", "medium": "🟡", "low": "🔵"}.get(s.priority, "•")
            print(f"   {icon} [{s.suggestion_type}] {s.rule_id}: {s.rationale[:80]}")


# ---------------------------------------------------------------------------
# Heuristics
# ---------------------------------------------------------------------------


def _suggest_for_rule(
    stat: RuleStat,
    total_runs: int,
    current_threshold: float,
    cfg: SuggesterConfig,
) -> list[RuleSuggestion]:
    suggestions: list[RuleSuggestion] = []

    # Not enough data
    if stat.total_findings < cfg.min_runs_for_suggestion and total_runs < cfg.never_fired_runs:
        return []

    # Never fired after many runs
    if stat.total_findings == 0 and total_runs >= cfg.never_fired_runs:
        suggestions.append(
            RuleSuggestion(
                suggestion_type="disable_candidate",
                rule_id=stat.rule_id,
                rationale=(
                    f"Never fired in {total_runs} runs. Either this rule doesn't apply "
                    f"to this codebase or the grounding doesn't cover the relevant domain."
                ),
                priority="low",
            )
        )
        return suggestions

    # High hallucination rate → raise threshold or manual review
    if stat.total_findings >= cfg.min_runs_for_suggestion:
        if stat.hallucination_rate >= cfg.hallucination_rate_high:
            new_threshold = min(0.99, current_threshold + cfg.threshold_step * 2)
            priority = "high" if stat.hallucination_rate >= 0.50 else "medium"
            suggestions.append(
                RuleSuggestion(
                    suggestion_type="review_manually" if priority == "high" else "threshold_adjustment",
                    rule_id=stat.rule_id,
                    rationale=(
                        f"Hallucination rate {stat.hallucination_rate:.0%} "
                        f"({stat.hallucinations}/{stat.passed + stat.hallucinations} findings "
                        f"intercepted by Meta-Review). This rule may be producing unreliable "
                        f"evidence_quotes. Review the grounding source and examples."
                    ),
                    current_threshold=current_threshold,
                    suggested_threshold=new_threshold,
                    priority=priority,
                )
            )

        # Mostly silenced → lower the threshold or review the rule
        elif stat.silence_rate >= cfg.silence_rate_high and stat.silenced >= cfg.min_runs_for_suggestion:
            new_threshold = max(0.50, current_threshold - cfg.threshold_step)
            suggestions.append(
                RuleSuggestion(
                    suggestion_type="threshold_adjustment",
                    rule_id=stat.rule_id,
                    rationale=(
                        f"{stat.silence_rate:.0%} of findings are silenced "
                        f"({stat.silenced}/{stat.total_findings}). "
                        f"The rule may be useful but the confidence is consistently just below "
                        f"threshold. Consider lowering the threshold to see if these are real "
                        f"findings, or rewrite the rule for higher confidence."
                    ),
                    current_threshold=current_threshold,
                    suggested_threshold=new_threshold,
                    priority="medium",
                )
            )

        # Trustworthy, high-volume rule → promote or document
        elif (
            stat.hallucination_rate <= cfg.hallucination_rate_low
            and stat.passed >= cfg.min_runs_for_suggestion * 2
        ):
            suggestions.append(
                RuleSuggestion(
                    suggestion_type="enable_candidate",
                    rule_id=stat.rule_id,
                    rationale=(
                        f"High-volume rule ({stat.passed} passed findings) with low "
                        f"hallucination rate ({stat.hallucination_rate:.0%}). "
                        f"Consider adding detailed documentation and examples to the grounding."
                    ),
                    priority="low",
                )
            )

    return suggestions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def suggest_calibrations(
    history: FindingsHistory,
    current_threshold: float = 0.80,
    cfg: SuggesterConfig | None = None,
) -> CalibrationReport:
    """Analyze findings history and produce calibration suggestions.

    Args:
        history:           FindingsHistory from build_history().
        current_threshold: The configured confidence_threshold.
        cfg:               Tuning parameters (defaults if None).

    Returns:
        CalibrationReport with suggestions and threshold adjustments.
    """
    if cfg is None:
        cfg = SuggesterConfig()

    report = CalibrationReport(
        built_at=datetime.now(tz=timezone.utc).isoformat(),
        current_threshold=current_threshold,
    )

    total_runs = len(history.runs)

    for stat in history.rule_stats:
        report.analyzed_rules += 1

        if (
            stat.total_findings < cfg.min_runs_for_suggestion
            and total_runs < cfg.never_fired_runs
        ):
            report.rules_skipped_insufficient_data += 1
            continue

        suggestions = _suggest_for_rule(stat, total_runs, current_threshold, cfg)
        report.suggestions.extend(suggestions)

        # Build threshold adjustment entries for actionable changes
        for s in suggestions:
            if (
                s.suggestion_type == "threshold_adjustment"
                and s.suggested_threshold is not None
                and s.current_threshold is not None
                and abs(s.suggested_threshold - s.current_threshold) >= cfg.threshold_step
            ):
                report.threshold_adjustments.append(
                    ThresholdAdjustment(
                        rule_id=s.rule_id,
                        current=s.current_threshold,
                        suggested=s.suggested_threshold,
                        reason=s.rationale[:100] + "...",
                    )
                )

    # Sort: high priority first, then by rule_id
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    report.suggestions.sort(key=lambda s: (priority_rank.get(s.priority, 9), s.rule_id))

    return report
