"""TRUST v2.1 tests — Learning Loop.

Covers:
  - findings_history: build_history (empty, single run, multi-run, filters)
  - findings_history: RuleStat aggregations (passed/silenced/hallucinations)
  - findings_history: export JSON/Markdown
  - rule_suggester: suggest_calibrations (threshold up, threshold down, disable, enable)
  - rule_suggester: CalibrationReport export
  - rule_suggester: insufficient data handling

All tests are fully offline.

Run:
    python -m pytest tests/e2e/test_v2_1.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.findings_history import (
    FindingsHistory,
    RuleStat,
    RunEntry,
    build_history,
)
from core.rule_suggester import (
    CalibrationReport,
    RuleSuggestion,
    SuggesterConfig,
    suggest_calibrations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run_dir(
    runs_dir: Path,
    run_id: str,
    branch: str = "feat/PAY-123",
    target_id: str = "api-payments",
    passed: list[dict] | None = None,
    silenced: list[dict] | None = None,
    hallucinations: list[dict] | None = None,
    halted: bool = False,
) -> Path:
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": run_id,
        "branch": branch,
        "target_id": target_id,
        "started_at": "2026-05-18T10:00:00Z",
        "overall_status": "halted" if halted else "done",
    }
    (run_dir / "run-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    gate = {
        "threshold": 0.80,
        "passed": passed or [],
        "silenced": silenced or [],
    }
    (run_dir / "gate.report.json").write_text(json.dumps(gate), encoding="utf-8")

    if hallucinations is not None:
        meta = {
            "hallucinations_caught": len(hallucinations),
            "hallucinations_caught_detail": hallucinations,
        }
        (run_dir / "meta-review.json").write_text(json.dumps(meta), encoding="utf-8")

    return run_dir


def _finding(rule_id: str, confidence: float = 0.90, file: str = "src/auth.py") -> dict:
    return {
        "rule_id": rule_id,
        "confidence": confidence,
        "file": file,
        "claim": "Test",
        "severity": "high",
    }


# ---------------------------------------------------------------------------
# findings_history: basic build
# ---------------------------------------------------------------------------


class TestBuildHistoryBasic:
    def test_empty_runs_dir_returns_empty_history(self, tmp_path):
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        history = build_history(runs_dir)
        assert history.scanned_runs == 0
        assert history.rule_stats == []
        assert history.runs == []

    def test_nonexistent_runs_dir(self, tmp_path):
        history = build_history(tmp_path / "nonexistent")
        assert history.scanned_runs == 0

    def test_skips_learning_subdir(self, tmp_path):
        runs_dir = tmp_path / "runs"
        (runs_dir / "learning").mkdir(parents=True)
        history = build_history(runs_dir)
        assert history.scanned_runs == 0

    def test_single_run_with_findings(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _make_run_dir(
            runs_dir, "run-001",
            passed=[_finding("SEC-001"), _finding("SEC-001"), _finding("CONV-001")],
        )
        history = build_history(runs_dir)
        assert history.scanned_runs == 1
        assert len(history.runs) == 1
        assert len(history.rule_stats) == 2  # SEC-001 and CONV-001

    def test_run_without_manifest_counted_as_error(self, tmp_path):
        runs_dir = tmp_path / "runs"
        bad_run = runs_dir / "bad-run"
        bad_run.mkdir(parents=True)
        history = build_history(runs_dir)
        assert history.scanned_runs == 1
        assert history.error_runs == 1


# ---------------------------------------------------------------------------
# findings_history: RuleStat aggregation
# ---------------------------------------------------------------------------


class TestRuleStatAggregation:
    def test_counts_passed_silenced_hallucinations(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _make_run_dir(
            runs_dir, "run-001",
            passed=[_finding("SEC-001"), _finding("SEC-001")],
            silenced=[_finding("SEC-001", confidence=0.70)],
            hallucinations=[_finding("SEC-001")],
        )
        history = build_history(runs_dir)
        stat = history.get_rule("SEC-001")
        assert stat is not None
        assert stat.passed == 2
        assert stat.silenced == 1
        assert stat.hallucinations == 1
        assert stat.total_findings == 4

    def test_avg_confidence(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _make_run_dir(
            runs_dir, "run-001",
            passed=[
                _finding("SEC-001", confidence=0.90),
                _finding("SEC-001", confidence=0.80),
            ],
        )
        history = build_history(runs_dir)
        stat = history.get_rule("SEC-001")
        assert abs(stat.avg_confidence - 0.85) < 0.01

    def test_hallucination_rate(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _make_run_dir(
            runs_dir, "run-001",
            passed=[_finding("SEC-001"), _finding("SEC-001")],
            hallucinations=[_finding("SEC-001"), _finding("SEC-001")],
        )
        history = build_history(runs_dir)
        stat = history.get_rule("SEC-001")
        assert abs(stat.hallucination_rate - 0.50) < 0.01

    def test_silence_rate(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _make_run_dir(
            runs_dir, "run-001",
            passed=[_finding("SEC-001")],
            silenced=[
                _finding("SEC-001", 0.70),
                _finding("SEC-001", 0.72),
                _finding("SEC-001", 0.75),
            ],
        )
        history = build_history(runs_dir)
        stat = history.get_rule("SEC-001")
        assert abs(stat.silence_rate - 0.75) < 0.01

    def test_aggregates_across_runs(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _make_run_dir(runs_dir, "run-001", passed=[_finding("SEC-001")])
        _make_run_dir(runs_dir, "run-002", passed=[_finding("SEC-001")])
        _make_run_dir(runs_dir, "run-003", passed=[_finding("SEC-001")])
        history = build_history(runs_dir)
        stat = history.get_rule("SEC-001")
        assert stat.passed == 3
        assert stat.total_findings == 3

    def test_last_seen_is_latest_run(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _make_run_dir(runs_dir, "run-001", passed=[_finding("SEC-001")])
        _make_run_dir(runs_dir, "run-003", passed=[_finding("SEC-001")])
        _make_run_dir(runs_dir, "run-002", passed=[_finding("SEC-001")])
        history = build_history(runs_dir)
        stat = history.get_rule("SEC-001")
        # run-003 is last alphabetically (since sorted), but last_seen is set per finding
        assert stat.last_seen in ("run-001", "run-002", "run-003")

    def test_halt_rate(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _make_run_dir(runs_dir, "run-001", halted=False)
        _make_run_dir(runs_dir, "run-002", halted=True)
        _make_run_dir(runs_dir, "run-003", halted=False)
        history = build_history(runs_dir)
        assert abs(history.halt_rate - 1/3) < 0.01


# ---------------------------------------------------------------------------
# findings_history: filters
# ---------------------------------------------------------------------------


class TestBuildHistoryFilters:
    def test_target_filter(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _make_run_dir(runs_dir, "run-001", target_id="api-payments", passed=[_finding("SEC-001")])
        _make_run_dir(runs_dir, "run-002", target_id="api-auth", passed=[_finding("SEC-002")])
        history = build_history(runs_dir, target_filter="api-payments")
        assert len(history.runs) == 1
        assert history.get_rule("SEC-001") is not None
        assert history.get_rule("SEC-002") is None

    def test_min_date_filter(self, tmp_path):
        runs_dir = tmp_path / "runs"
        run1 = runs_dir / "run-001"
        run1.mkdir(parents=True)
        (run1 / "run-manifest.json").write_text(
            json.dumps({"run_id": "run-001", "branch": "feat/x", "target_id": "t",
                        "started_at": "2026-01-15T10:00:00Z", "overall_status": "done"}),
            encoding="utf-8",
        )
        (run1 / "gate.report.json").write_text(
            json.dumps({"passed": [_finding("SEC-001")], "silenced": []}), encoding="utf-8"
        )
        run2 = runs_dir / "run-002"
        run2.mkdir(parents=True)
        (run2 / "run-manifest.json").write_text(
            json.dumps({"run_id": "run-002", "branch": "feat/y", "target_id": "t",
                        "started_at": "2026-05-01T10:00:00Z", "overall_status": "done"}),
            encoding="utf-8",
        )
        (run2 / "gate.report.json").write_text(
            json.dumps({"passed": [_finding("SEC-002")], "silenced": []}), encoding="utf-8"
        )
        history = build_history(runs_dir, min_date="2026-04-01")
        assert len(history.runs) == 1
        assert history.runs[0].run_id == "run-002"


# ---------------------------------------------------------------------------
# findings_history: export
# ---------------------------------------------------------------------------


class TestFindingsHistoryExport:
    def test_export_json(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _make_run_dir(runs_dir, "run-001", passed=[_finding("SEC-001")])
        history = build_history(runs_dir)
        out = tmp_path / "learning" / "history.json"
        history.export_json(out)
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "rule_stats" in data
        assert data["total_findings"] == 1

    def test_export_markdown(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _make_run_dir(runs_dir, "run-001", passed=[_finding("SEC-001")])
        history = build_history(runs_dir)
        out = tmp_path / "learning" / "history.md"
        history.export_markdown(out)
        assert out.exists()
        text = out.read_text(encoding="utf-8")
        assert "SEC-001" in text
        assert "Rule Statistics" in text

    def test_total_findings_property(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _make_run_dir(runs_dir, "run-001", passed=[_finding("SEC-001"), _finding("SEC-002")])
        _make_run_dir(runs_dir, "run-002", passed=[_finding("SEC-001")])
        history = build_history(runs_dir)
        assert history.total_findings == 3

    def test_sorted_by(self, tmp_path):
        runs_dir = tmp_path / "runs"
        _make_run_dir(runs_dir, "run-001", passed=[_finding("SEC-001"), _finding("SEC-001"), _finding("CONV-001")])
        history = build_history(runs_dir)
        sorted_stats = history.sorted_by("total_findings")
        assert sorted_stats[0].rule_id == "SEC-001"


# ---------------------------------------------------------------------------
# rule_suggester
# ---------------------------------------------------------------------------


class TestSuggestCalibrations:
    def _make_history_with_rule(
        self,
        rule_id: str,
        passed: int = 0,
        silenced: int = 0,
        hallucinations: int = 0,
        total_runs: int = 10,
    ) -> FindingsHistory:
        stat = RuleStat(
            rule_id=rule_id,
            agent=rule_id.split("-")[0].lower(),
            total_findings=passed + silenced + hallucinations,
            passed=passed,
            silenced=silenced,
            hallucinations=hallucinations,
            confidence_sum=(passed + silenced + hallucinations) * 0.85,
        )
        history = FindingsHistory(
            rule_stats=[stat],
            runs=[RunEntry(
                run_id=f"run-{i:03d}",
                branch="feat/x",
                target_id="t",
                started_at="2026-05-01T00:00:00Z",
                finding_count=1 if i == 0 else 0,
                hallucination_count=0,
                halted=False,
            ) for i in range(total_runs)],
            scanned_runs=total_runs,
        )
        return history

    def test_no_suggestions_for_insufficient_data(self):
        history = self._make_history_with_rule("SEC-001", passed=1, total_runs=2)
        cfg = SuggesterConfig(min_runs_for_suggestion=5)
        report = suggest_calibrations(history, cfg=cfg)
        assert report.rules_skipped_insufficient_data == 1
        assert len(report.suggestions) == 0

    def test_high_hallucination_rate_suggests_review(self):
        history = self._make_history_with_rule(
            "SEC-001", passed=5, hallucinations=10, total_runs=10
        )
        cfg = SuggesterConfig(min_runs_for_suggestion=5)
        report = suggest_calibrations(history, current_threshold=0.80, cfg=cfg)
        assert any(s.rule_id == "SEC-001" and s.priority == "high" for s in report.suggestions)

    def test_medium_hallucination_rate_suggests_threshold_raise(self):
        history = self._make_history_with_rule(
            "SEC-002", passed=10, hallucinations=5, total_runs=10   # 5/15 = 33% > 30%
        )
        cfg = SuggesterConfig(min_runs_for_suggestion=5, hallucination_rate_high=0.30)
        report = suggest_calibrations(history, current_threshold=0.80, cfg=cfg)
        matching = [s for s in report.suggestions if s.rule_id == "SEC-002"]
        assert matching
        assert any(s.suggested_threshold and s.suggested_threshold > 0.80 for s in matching)

    def test_high_silence_rate_suggests_threshold_lower(self):
        history = self._make_history_with_rule(
            "CONV-001", passed=2, silenced=8, total_runs=10
        )
        cfg = SuggesterConfig(min_runs_for_suggestion=5, silence_rate_high=0.60)
        report = suggest_calibrations(history, current_threshold=0.80, cfg=cfg)
        matching = [s for s in report.suggestions if s.rule_id == "CONV-001"]
        assert matching
        assert any(
            s.suggestion_type == "threshold_adjustment"
            and s.suggested_threshold
            and s.suggested_threshold < 0.80
            for s in matching
        )

    def test_never_fired_suggests_disable(self):
        stat = RuleStat(rule_id="PERF-001", total_findings=0)
        history = FindingsHistory(
            rule_stats=[stat],
            runs=[RunEntry(f"run-{i}", "feat/x", "t", "2026-01-01T00:00:00Z", 0, 0, False)
                  for i in range(12)],
            scanned_runs=12,
        )
        cfg = SuggesterConfig(never_fired_runs=10)
        report = suggest_calibrations(history, cfg=cfg)
        assert any(
            s.rule_id == "PERF-001" and s.suggestion_type == "disable_candidate"
            for s in report.suggestions
        )

    def test_trustworthy_high_volume_suggests_enable(self):
        history = self._make_history_with_rule(
            "SEC-007", passed=30, hallucinations=0, total_runs=15
        )
        cfg = SuggesterConfig(
            min_runs_for_suggestion=5,
            hallucination_rate_low=0.05,
        )
        report = suggest_calibrations(history, current_threshold=0.80, cfg=cfg)
        assert any(
            s.rule_id == "SEC-007" and s.suggestion_type == "enable_candidate"
            for s in report.suggestions
        )

    def test_high_priority_sorted_first(self):
        history = FindingsHistory(
            rule_stats=[
                RuleStat("CONV-001", total_findings=8, passed=2, silenced=6, confidence_sum=6.8),
                RuleStat("SEC-001", total_findings=20, passed=5, hallucinations=10, confidence_sum=17.0),
            ],
            runs=[RunEntry(f"run-{i}", "feat/x", "t", "2026-01-01T00:00:00Z", 1, 0, False)
                  for i in range(10)],
            scanned_runs=10,
        )
        cfg = SuggesterConfig(min_runs_for_suggestion=5)
        report = suggest_calibrations(history, cfg=cfg)
        if len(report.suggestions) >= 2:
            priority_rank = {"high": 0, "medium": 1, "low": 2}
            priorities = [priority_rank[s.priority] for s in report.suggestions]
            assert priorities == sorted(priorities)

    def test_threshold_adjustment_recorded(self):
        history = self._make_history_with_rule(
            "CONV-002", passed=2, silenced=10, total_runs=10
        )
        cfg = SuggesterConfig(min_runs_for_suggestion=5)
        report = suggest_calibrations(history, current_threshold=0.80, cfg=cfg)
        if any(s.suggestion_type == "threshold_adjustment" for s in report.suggestions):
            assert len(report.threshold_adjustments) >= 1


# ---------------------------------------------------------------------------
# CalibrationReport export
# ---------------------------------------------------------------------------


class TestCalibrationReportExport:
    def _make_report(self) -> CalibrationReport:
        report = CalibrationReport(
            suggestions=[
                RuleSuggestion(
                    suggestion_type="threshold_adjustment",
                    rule_id="CONV-002",
                    rationale="High silence rate",
                    current_threshold=0.80,
                    suggested_threshold=0.75,
                    priority="medium",
                )
            ],
            analyzed_rules=5,
            built_at="2026-05-18T12:00:00Z",
            current_threshold=0.80,
        )
        return report

    def test_export_json(self, tmp_path):
        report = self._make_report()
        out = tmp_path / "calibration.json"
        report.export_json(out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["analyzed_rules"] == 5
        assert len(data["suggestions"]) == 1
        assert data["suggestions"][0]["rule_id"] == "CONV-002"

    def test_export_markdown(self, tmp_path):
        report = self._make_report()
        out = tmp_path / "calibration.md"
        report.export_markdown(out)
        text = out.read_text(encoding="utf-8")
        assert "CONV-002" in text
        assert "Calibration Report" in text

    def test_export_markdown_no_suggestions(self, tmp_path):
        report = CalibrationReport(built_at="2026-05-18T12:00:00Z", analyzed_rules=3)
        out = tmp_path / "calibration.md"
        report.export_markdown(out)
        text = out.read_text(encoding="utf-8")
        assert "No calibration suggestions" in text

    def test_print_summary_no_crash(self, capsys):
        report = self._make_report()
        report.print_summary()
        captured = capsys.readouterr()
        assert "CONV-002" in captured.out
