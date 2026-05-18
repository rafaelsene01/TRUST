# /trust learn from-history — Protocol

Reads all run artifacts, aggregates per-rule statistics, and writes calibration suggestions.

## Execution steps

1. Resolve `$TRUST_SETUP_PATH` and load `trust.config.yaml`
2. Call `core/findings_history.build_history(runs_dir, target_filter, min_date)`
3. Call `core/rule_suggester.suggest_calibrations(history, current_threshold)`
4. Write `history.export_json(...)` → `runs/learning/YYYY-MM-DD-history.json`
5. Write `report.export_json(...)` → `runs/learning/YYYY-MM-DD-calibration.json`
6. Call `report.print_summary()` to display output
7. Remind user to run `/trust learn apply` to apply threshold changes

## Output example

```
📊 Learning from 47 runs (target: api-payments)

   Rules analyzed: 34
   Findings total: 312
   Hallucination rate: 8/312 (2.6%)
   HALT rate: 2/47 (4.3%)

📋 Calibration suggestions:

   🔴 [review_manually] SEC-003: Hallucination rate 48% — 11/23 findings
      intercepted by Meta-Review. Review grounding and examples.

   🟡 [threshold_adjustment] CONV-002: 68% of findings silenced.
      Threshold 80% → 75% suggested.

   🔵 [enable_candidate] SEC-007: 29 passed findings, 0% hallucination.
      Consider expanding coverage and documenting examples.

📄 Reports written to:
   ~/work/payments-team-trust/runs/learning/2026-05-18-history.json
   ~/work/payments-team-trust/runs/learning/2026-05-18-calibration.json
```

## Notes

- A rule with insufficient data is not shown — run more PRs first.
- `review_manually` suggestions are never auto-applied — always require human judgment.
