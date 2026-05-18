# PROTOCOL — trust-second-pass

> Step-by-step execution for the Second Pass aggregate check. Load before starting.

---

## Step 0 — Verify inputs

Confirm all required agent outputs exist in `<run-dir>/agents/`:

```
security.findings.json    (required)
security.second-pass.json (required)
contracts.findings.json   (required if agent ran)
contracts.second-pass.json
data.findings.json
data.second-pass.json
performance.findings.json
performance.second-pass.json
conventions.findings.json
conventions.second-pass.json
tests.findings.json
tests.second-pass.json
```

If any required file is missing → **halt** with "missing agent output: <file>".

---

## Step 1 — Parse the diff into hunks

Read `<run-dir>/diff.patch`. Split into hunks by `@@` markers.

For each hunk, record:
- `hunk_id` = `"<file>:<line_start>-<line_end>"` (new-file lines from the `+N,M` side of `@@`)
- `file` = filename from the `+++ b/<file>` header above the hunk

Build: `all_hunks: list[hunk_id]`

---

## Step 2 — Build the accounting index

For each agent, collect:

**From `<agent>.findings.json`:**
- For each finding: mark `finding.file + lines (line_start..line_end)` as accounted

**From `<agent>.second-pass.json`:**
- For each non_finding: mark `non_finding.hunk_id` as accounted

Build: `accounted_hunks: set[hunk_id]`

---

## Step 3 — Cross-reference

```python
unaccounted = [h for h in all_hunks if h not in accounted_hunks]
```

For each unaccounted hunk: record `file`, `line_start`, `line_end`, and the list of agents that reviewed the file (to help diagnose the gap).

---

## Step 4 — Write aggregate report

Write `<run-dir>/second-pass/aggregate.json` using the schema from `SKILL.md`.

Set `halt_required = (len(unaccounted) > 0)`.

---

## Step 5 — Return result to orchestrator

If `halt_required: false` → orchestrator advances to Phase 4 (Precision Gate).

If `halt_required: true` → orchestrator HALTS. The unaccounted hunks are listed
in the report for the developer to investigate which agent missed them.

---

## Common mistakes to avoid

- **Hunk ID mismatch**: use the new-file line numbers (from `+N` in `@@`), not the old-file numbers
- **Forgetting context lines**: `@@` context lines (no `+` or `-`) count as part of the hunk's line range
- **Assuming an agent covered a file**: an agent marks only the files it evaluated. If a file's hunk is not in any agent's findings OR non-findings, it's unaccounted
