# /trust runs

Inspect the history of TRUST review runs stored in the setup repo.

## Usage

```
/trust runs list [--limit <n>] [--target <repo-slug>] [--status halted|done|all]
/trust runs show <run-id>
/trust runs clean [--older-than <days>] [--dry-run]
```

## Subcommands

| Subcommand | What it does |
| --- | --- |
| `list` | Shows recent runs in a table with status, branch, and date |
| `show` | Detailed view of a single run — phases, timings, finding counts |
| `clean` | Removes run artifacts older than N days (HALT runs require `--force`) |

## `list` output format

```
╭─ TRUST runs — recent 10 ──────────────────────────────────────╮
│  # RUN ID           BRANCH              STATUS  DATE         │
│  1 feat-PAY-123-a1b feat/PAY-123        ✅ done  2026-05-17   │
│  2 feat-PAY-120-c2d feat/PAY-120        🛑 halt  2026-05-16   │
╰───────────────────────────────────────────────────────────────╯
```

## When to load

| File | When to load |
| --- | --- |
| `commands/references/runs-show.md` | Any subcommand — contains execution steps and full output formats |
