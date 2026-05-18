# /trust learn apply — Protocol

Reads the most recent calibration report and applies threshold adjustments to `trust.config.yaml`.

## Execution steps

1. Read the most recent `runs/learning/*-calibration.json`
2. If `--dry-run`, print what would change and exit
3. Back up `trust.config.yaml` → `trust.config.yaml.bak`
4. Update `confidence_threshold` in `trust.config.yaml` with adjusted values
   (per-rule thresholds are written as inline comments — global threshold
   adjustment applied when all suggestions point in the same direction;
   otherwise listed individually with notes)
5. Print confirmation with what changed

## Output (dry-run)

```
🔍 Dry run — no files will be modified

   Would adjust:
   CONV-002: confidence_threshold 80% → 75%

   File: ~/work/payments-team-trust/trust.config.yaml
```

## Output (apply)

```
✅ Applied 1 threshold adjustment

   CONV-002: 80% → 75%

   Updated: ~/work/payments-team-trust/trust.config.yaml
   Backup:  ~/work/payments-team-trust/trust.config.yaml.bak
```

## Notes

- Only `confidence_threshold` is touched. Per-rule thresholds are a v2.2 feature.
- `review_manually` suggestions are never auto-applied.
- Always review `trust.config.yaml.bak` if something looks wrong after applying.
