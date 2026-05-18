# /trust stats

Display review metrics and team dashboard.

## Usage

```
/trust stats [--target <slug>] [--since <YYYY-MM-DD>] [--format json|markdown]
/trust stats rules [--sort total|hallucination|silence] [--top N]
/trust stats runs [--status halted|done|all] [--limit N]
```

## Subcommands

| Subcommand | What it does |
| --- | --- |
| `stats` | Overall metrics dashboard — runs, findings, hallucination rate, top rules |
| `stats rules` | Per-rule breakdown table, sortable by any metric |
| `stats runs` | Run history list with status, branch, and finding count |

## See also

- `/trust learn from-history` — generate calibration suggestions from this data
- `/trust runs list` — detailed run inspection

## When to load

| File | When to load |
| --- | --- |
| `commands/references/stats-dashboard.md` | Subcommand is `stats` (default) |
| `commands/references/stats-rules.md` | Subcommand is `stats rules` |
