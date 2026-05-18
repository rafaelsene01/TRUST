# /trust stats

Display review metrics and team dashboard.

---

## Usage

```
/trust stats [--target <slug>] [--since <YYYY-MM-DD>] [--format json|markdown]
/trust stats rules [--sort total|hallucination|silence] [--top N]
/trust stats runs [--status halted|done|all] [--limit N]
```

---

## Commands

### `stats` — overall metrics dashboard

```bash
/trust stats
/trust stats --target api-payments --since 2026-01-01
```

Displays a summary dashboard with team-level metrics.

**Output example:**

```
📊 TRUST Stats — payments-squad (last 30 days)
   ──────────────────────────────────────────

   Runs:            47 total  •  45 done  •  2 halted (4.3%)
   Findings:       312 total  •  298 passed  •  14 silenced
   Hallucinations:   8 intercepted (2.6% rate)
   Coverage:        6/6 agents active

   Top rules by volume:
   SEC-007   42 findings  •  0% hallucinations  ✅
   CONV-002  38 findings  •  3% hallucinations  ✅
   SEC-003   23 findings  •  48% hallucinations ⚠️  (run /trust learn from-history)

   Trend: +12% findings vs previous 30 days
          -3% hallucination rate vs previous 30 days
```

---

### `stats rules` — per-rule breakdown

```bash
/trust stats rules
/trust stats rules --sort hallucination --top 10
```

Shows the full rule statistics table, sortable by any metric.

**Output example:**

```
📋 Rule Statistics (sorted by total findings)

| Rule      | Findings | Passed | Silenced | Hallucinations | Avg Conf | Hallu% |
|-----------|----------|--------|----------|----------------|----------|--------|
| SEC-007   |       42 |     42 |        0 |              0 |     91%  |    0%  |
| CONV-002  |       38 |     31 |        7 |              1 |     83%  |    3%  |
| SEC-003   |       23 |     12 |        3 |             11 |     79%  |   48%  |
```

---

### `stats runs` — run history

```bash
/trust stats runs
/trust stats runs --status halted
/trust stats runs --limit 20
```

Lists runs with their status, branch, finding count, and duration.

---

## Protocol

When `/trust stats` is invoked:

1. Resolve `$TRUST_SETUP_PATH` and read `trust.config.yaml`
2. Call `core/findings_history.build_history(runs_dir, target_filter, min_date)`
3. Format output based on `--format` flag (default: human-readable terminal)
4. If `--format json`: write to stdout as JSON
5. If `--format markdown`: write to `runs/learning/stats-YYYY-MM-DD.md`

When `/trust stats rules` is invoked:

1. Build history (same as above)
2. Sort by requested field (default: total_findings descending)
3. Render as a Markdown table in the terminal

---

## Output format: JSON

```bash
/trust stats --format json
```

Produces:

```json
{
  "built_at": "2026-05-18T14:30:00Z",
  "runs_total": 47,
  "runs_halted": 2,
  "halt_rate": 0.043,
  "findings_total": 312,
  "findings_passed": 298,
  "findings_silenced": 14,
  "hallucinations_total": 8,
  "hallucination_rate": 0.026,
  "rule_stats": [...]
}
```

---

## Integration with CI

To fail CI when the hallucination rate exceeds a threshold:

```bash
trust_stats=$(trust stats --format json)
hallu_rate=$(echo "$trust_stats" | jq .hallucination_rate)
if (( $(echo "$hallu_rate > 0.10" | bc -l) )); then
  echo "⚠️  Hallucination rate ${hallu_rate} exceeds 10% — run /trust learn"
  exit 1
fi
```

---

## See also

- `/trust learn from-history` — generate calibration suggestions
- `/trust runs list` — inspect individual run history
- `/trust doctor` — full system health check
