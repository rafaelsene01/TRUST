# PROTOCOL — trust-performance-review

> Detailed execution protocol. Load this file before touching the diff.

---

## Step 0 — Verify environment

Before anything else, confirm:

- [ ] `TRUST_SETUP_PATH` env var is set and points to a valid setup repo
- [ ] `trust.config.yaml` exists in the setup root and is readable
- [ ] The current target's `target.yaml` has been resolved by the orchestrator
- [ ] The diff is available in the run directory (`<run-dir>/diff.patch`)

If any check fails, **halt** and return a structured error.

---

## Step 1 — Load grounding

Read the following files from the setup repo's `grounding/`:

- `01-architecture.md` — **your primary source of truth** (performance constraints, hot paths, SLA requirements)
- `04-data-model.md` — to understand what DB access patterns are expected/allowed
- `05-conventions.md` — to know approved async patterns and I/O conventions
- `07-adrs/` — ADRs that document known performance exceptions

Index sections by anchor.

If any required doc is missing → **halt**.

---

## Step 2 — Load checklist

Read `checklists/performance.checklist.md` from the setup repo. Parse into structured list.

If any rule lacks required fields → **halt**.

---

## Step 3 — Inventory diff files in domain

Files in the performance domain: service files, repository files, query files, background job files, cache layer files.

```
file_patterns: ["**/services/**", "**/repositories/**", "**/jobs/**",
                "**/workers/**", "**/queries/**", "**/resolvers/**",
                "**/*.service.*", "**/*.repository.*"]
```

Exclude pure test files unless the checklist explicitly covers test performance.

---

## Step 4 — Build the coverage matrix

For every `(rule × file)` pair, produce a verdict.

**Critical assessment per rule type:**

- **N+1 rules** (e.g. PERF-001): look for queries inside for/forEach/map loops in the SAME hunk. Do NOT speculate about calling code that may iterate — only flag what's visible in the diff.
- **Unbounded query rules** (e.g. PERF-002): look for `.findAll()`, `.find({})`, `SELECT *` without any LIMIT/pagination parameter visible in the same statement.
- **Timeout rules** (e.g. PERF-004): look for HTTP client calls, external API calls, or message queue producers without a `timeout` option visible in the call.
- **Blocking I/O rules** (e.g. PERF-005): look for synchronous file operations, synchronous crypto operations, or `readFileSync`/`writeFileSync` in async functions.

---

## Step 5 — Generate findings from violations

For every `violation` verdict, produce a finding using `references/FINDING_FORMAT.md`.

Critical reminders:
1. N+1 findings: quote the ENTIRE loop construct (for line + query line)
2. Never speculate about perf impact without evidence in the diff
3. Framework-aware: if the ORM batches automatically (DataLoader, Eager loading config), confidence drops significantly

---

## Step 6 — Validate findings before emitting

Self-check each finding.

---

## Step 7 — Run all validation scripts

```bash
python scripts/validate_coverage.py <run-dir>/agents/performance.coverage.json
```

---

## Step 8 — Self-attest Definition of Done

Read `references/DOD.md`, fill attestation, write to `<run-dir>/agents/performance.dod.json`.
