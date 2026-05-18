# /trust stats rules — Protocol

## Execution steps

1. Build history (same as `stats` dashboard)
2. Sort by requested field (default: `total_findings` descending)
3. Render as a Markdown table in the terminal

## Output example

```
📋 Rule Statistics (sorted by total findings)

| Rule      | Findings | Passed | Silenced | Hallucinations | Avg Conf | Hallu% |
|-----------|----------|--------|----------|----------------|----------|--------|
| SEC-007   |       42 |     42 |        0 |              0 |     91%  |    0%  |
| CONV-002  |       38 |     31 |        7 |              1 |     83%  |    3%  |
| SEC-003   |       23 |     12 |        3 |             11 |     79%  |   48%  |
```

## Sort options

| `--sort` value | Sorts by |
| --- | --- |
| `total` (default) | Total findings descending |
| `hallucination` | Hallucination rate descending |
| `silence` | Silence rate descending |
| `confidence` | Average confidence ascending |

`--top N` limits output to N rows.
