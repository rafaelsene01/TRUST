# /trust runs

Inspect the history of TRUST review runs stored in the setup repo.

## Usage

```
/trust runs list [--limit <n>] [--target <repo-slug>] [--status halted|done|all]
/trust runs show <run-id>
/trust runs clean [--older-than <days>] [--dry-run]
```

---

## Subcommands

### `list` — show recent runs

```
/trust runs list
/trust runs list --limit 20
/trust runs list --status halted
/trust runs list --target payments-api
```

Output format:
```
╭─ TRUST runs — recent 10 ──────────────────────────────────────╮
│                                                               │
│  # RUN ID           BRANCH              STATUS  DATE         │
│  1 feat-PAY-123-a1b feat/PAY-123        ✅ done  2026-05-17   │
│  2 feat-PAY-120-c2d feat/PAY-120        🛑 halt  2026-05-16   │
│  3 fix-AUTH-88-e3f  fix/AUTH-88         ✅ done  2026-05-15   │
│                                                               │
│  3 runs shown (2 done, 1 halted)                              │
╰───────────────────────────────────────────────────────────────╯
```

Flags:
| Flag | Default | Description |
| --- | --- | --- |
| `--limit` | 10 | Max runs to show |
| `--target` | all | Filter by target repo slug |
| `--status` | all | `halted` \| `done` \| `all` |

---

### `show` — inspect a specific run

```
/trust runs show feat-PAY-123-a1b
```

Output:
```
╭─ Run: feat-PAY-123-a1b ──────────────────────────────────────╮
│  Branch:   feat/PAY-123                                      │
│  Target:   payments-api                                      │
│  Started:  2026-05-17 14:23:11 UTC                           │
│  Duration: 4m32s                                             │
│  Status:   ✅ done                                           │
│                                                              │
│  Phases:                                                     │
│    ✅ Phase 0 — Trigger       (0.3s)                         │
│    ✅ Phase 1 — Grounding     (1.2s)  7 docs loaded          │
│    ✅ Phase 2 — Agents        (4m18s) 6 agents               │
│    ✅ Phase 3 — Second Pass   (0.8s)  0 hunks unaccounted    │
│    ✅ Phase 4 — Precision Gate(0.1s)  12 passed, 3 silenced  │
│    ✅ Phase 5 — Meta-Review   (0.5s)  12 validated, 0 hallu  │
│    ⏭  Phase 6 — Traceability  (skipped — disabled in config) │
│    ✅ Phase 7 — Output        (0.2s)  REVIEW.md written      │
│                                                              │
│  Findings: 3 critical, 4 high, 5 medium, 0 low              │
│  Output:   runs/feat-PAY-123-a1b/REVIEW.md                   │
╰──────────────────────────────────────────────────────────────╯
```

---

### `clean` — remove old run artifacts

```
/trust runs clean --older-than 30
/trust runs clean --older-than 7 --dry-run
```

Removes run directories older than `<n>` days.
`--dry-run` prints what would be removed without deleting.

Runs with status `halted` are always listed with a confirmation prompt,
since HALT artifacts are often needed for post-mortems.

Output:
```
  Would remove 4 runs older than 30 days (312 MB):
    ✅ feat-PAY-100-x1y (done,  2026-04-10, 12 MB)
    ✅ fix-LOG-55-z2w   (done,  2026-04-08, 8 MB)
    ✅ feat-UI-92-a3b   (done,  2026-04-05, 5 MB)
    🛑 feat-PAY-89-c4d  (HALT,  2026-04-04, 287 MB) ← requires --force to delete

  Run without --dry-run to delete.
```

---

## Execution steps (all subcommands)

**Step 1 — Validate environment**

Check `TRUST_SETUP_PATH` is set. If not:
```
✗ TRUST_SETUP_PATH is not set.
→ Next action: export TRUST_SETUP_PATH=/path/to/your-trust-setup
```

**Step 2 — Find runs directory**

Read `runs.base_dir` from `trust.config.yaml` (default: `./runs`).
Enumerate subdirectories — each is a run if it contains `run-manifest.json`.

**Step 3 — Parse run manifests**

Read each `run-manifest.json` to extract: `run_id`, `branch`, `target_id`,
`started_at`, `overall_status`, phase durations, finding counts.

**Step 4 — Execute subcommand**

For `list`: format and print the table.
For `show`: read full manifest + REVIEW.md header + print detail view.
For `clean`: compute sizes, filter by age, ask confirmation for HALT runs.
