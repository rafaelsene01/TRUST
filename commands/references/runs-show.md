# /trust runs — Execution Protocol

All subcommands (`list`, `show`, `clean`) share these setup steps.

## Shared steps (all subcommands)

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

Read each `run-manifest.json` to extract:
`run_id`, `branch`, `target_id`, `started_at`, `overall_status`, phase durations, finding counts.

**Step 4 — Execute subcommand**

- `list`: format and print the table
- `show`: read full manifest + `REVIEW.md` header + print detail view
- `clean`: compute sizes, filter by age, ask confirmation for HALT runs

## `show` output format

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

## `clean` output format

```
  Would remove 4 runs older than 30 days (312 MB):
    ✅ feat-PAY-100-x1y (done,  2026-04-10, 12 MB)
    ✅ fix-LOG-55-z2w   (done,  2026-04-08, 8 MB)
    ✅ feat-UI-92-a3b   (done,  2026-04-05, 5 MB)
    🛑 feat-PAY-89-c4d  (HALT,  2026-04-04, 287 MB) ← requires --force to delete
```

HALT runs always require explicit confirmation (`--force`).
