# /trust stats — Dashboard Protocol

## Execution steps

1. Resolve `$TRUST_SETUP_PATH` and read `trust.config.yaml`
2. Call `core/findings_history.build_history(runs_dir, target_filter, min_date)`
3. Format output based on `--format` flag (default: human-readable terminal)
4. If `--format json`: write to stdout as JSON
5. If `--format markdown`: write to `runs/learning/stats-YYYY-MM-DD.md`

## Output — terminal

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

## Output — JSON (`--format json`)

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

## CI integration

```bash
trust_stats=$(trust stats --format json)
hallu_rate=$(echo "$trust_stats" | jq .hallucination_rate)
if (( $(echo "$hallu_rate > 0.10" | bc -l) )); then
  echo "⚠️  Hallucination rate ${hallu_rate} exceeds 10% — run /trust learn"
  exit 1
fi
```
