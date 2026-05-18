# /trust learn

Analyze past review history and propose calibration improvements.

---

## Usage

```
/trust learn from-history [--target <slug>] [--min-runs <N>] [--since <YYYY-MM-DD>]
/trust learn apply [--dry-run]
/trust learn status
```

---

## Commands

### `from-history` — analyze past runs and generate suggestions

```bash
/trust learn from-history
/trust learn from-history --target api-payments
/trust learn from-history --min-runs 10 --since 2026-01-01
```

Reads all run artifacts in `$TRUST_SETUP_PATH/runs/`, aggregates per-rule
statistics, and writes two files to `runs/learning/`:

- `YYYY-MM-DD-history.json` — raw rule statistics
- `YYYY-MM-DD-calibration.json` — calibration suggestions

**Output example:**

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

---

### `apply` — apply threshold adjustments

```bash
/trust learn apply
/trust learn apply --dry-run
```

Reads the most recent `runs/learning/*-calibration.json` and applies
the `threshold_adjustments` block to `trust.config.yaml`.

With `--dry-run`: shows what would change without modifying any files.

**Output (dry-run):**

```
🔍 Dry run — no files will be modified

   Would adjust:
   CONV-002: confidence_threshold 80% → 75%

   File: ~/work/payments-team-trust/trust.config.yaml
```

**Output (apply):**

```
✅ Applied 1 threshold adjustment

   CONV-002: 80% → 75%

   Updated: ~/work/payments-team-trust/trust.config.yaml
   Backup:  ~/work/payments-team-trust/trust.config.yaml.bak
```

---

### `status` — show current learning state

```bash
/trust learn status
```

Shows when the last analysis was run, how many runs are in the history,
and whether there are pending suggestions.

---

## Protocol

When `/trust learn from-history` is invoked:

1. Resolve `$TRUST_SETUP_PATH` and load `trust.config.yaml`
2. Call `core/findings_history.build_history(runs_dir, target_filter, min_date)`
3. Call `core/rule_suggester.suggest_calibrations(history, current_threshold)`
4. Write `history.export_json(...)` and `report.export_json(...)`
5. Call `report.print_summary()` to display the output
6. Remind user to run `/trust learn apply` to apply threshold changes

When `/trust learn apply` is invoked:

1. Read the most recent `runs/learning/*-calibration.json`
2. If `--dry-run`, print what would change and exit
3. Back up `trust.config.yaml` → `trust.config.yaml.bak`
4. Update `confidence_threshold` in `trust.config.yaml` with adjusted values
   (per-rule thresholds are written as inline comments for now — global
   threshold adjustment is applied when all suggestions point in the same
   direction; otherwise, list individually with notes)
5. Print confirmation with what changed

---

## Notes

- Suggestions are **proposals, not automatic changes**. Always review
  before applying.
- A rule with "insufficient data" is not shown — run more PRs first.
- `/trust learn apply` only touches `confidence_threshold` in the global
  config. Per-rule thresholds are a v2.2 feature.
- The `review_manually` suggestion type is never auto-applied — it always
  requires human judgment.
