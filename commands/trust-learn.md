# /trust learn

Analyze past review history and propose calibration improvements.

## Usage

```
/trust learn from-history [--target <slug>] [--min-runs <N>] [--since <YYYY-MM-DD>]
/trust learn apply [--dry-run]
/trust learn status
```

## Subcommands

| Subcommand | What it does |
| --- | --- |
| `from-history` | Reads run artifacts, aggregates per-rule stats, writes calibration suggestions |
| `apply` | Applies threshold adjustments from latest calibration report to `trust.config.yaml` |
| `status` | Shows when last analysis ran, how many runs in history, and pending suggestions |

## When to load

| File | When to load |
| --- | --- |
| `commands/references/learn-from-history.md` | Subcommand is `from-history` |
| `commands/references/learn-apply.md` | Subcommand is `apply` |
