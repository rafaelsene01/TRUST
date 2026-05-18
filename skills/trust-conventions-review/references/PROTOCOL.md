# PROTOCOL — trust-conventions-review

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

- `05-conventions.md` — **your primary source of truth** (naming, logging, error handling, file structure)
- `01-architecture.md` — to understand module boundaries and layer conventions
- `07-adrs/` — ADRs that document intentional convention exceptions

Index sections by anchor.

If any required doc is missing → **halt**.

---

## Step 2 — Load checklist

Read `checklists/conventions.checklist.md` from the setup repo. Parse into structured list.

If any rule lacks required fields → **halt**.

---

## Step 3 — Inventory diff files in domain

Conventions applies to all source files, excluding generated files and vendor/node_modules.

```
file_patterns: ["**/*.ts", "**/*.js", "**/*.py", "**/*.go", "**/*.java",
                "**/*.rb", "**/*.cs", "**/*.kt", "**/*.swift"]
path_filters.ignore: ["**/node_modules/**", "**/vendor/**", "**/*.generated.*",
                       "**/dist/**", "**/build/**"]
```

Adapt to the project's language stack as declared in `trust.config.yaml`.

---

## Step 4 — Build the coverage matrix

For every `(rule × file)` pair, produce a verdict.

**Conventions are often `not_applicable`** when a rule targets a specific code pattern (e.g. a logging rule) but the file has no logging statements. Mark N/A with a one-sentence reason — do not force-evaluate.

**Key assessment:**
- Naming rules: look for newly introduced identifiers (functions, classes, variables) in `+` lines
- Logging rules: look for any logging/console statement in `+` lines
- Error handling rules: look for try/catch, error returns, or exception handlers in `+` lines
- Import rules: look for new import statements in `+` lines

---

## Step 5 — Generate findings from violations

For every `violation` verdict, produce a finding using `references/FINDING_FORMAT.md`.

Severity calibration for conventions:
- `high`: convention exists because of a documented incident (see ADR); violation will likely cause the same incident
- `medium`: convention violation makes code less maintainable but won't cause immediate failures
- `low`: pure style, no functional impact
- `critical`: **never** for convention findings

---

## Step 6 — Validate findings before emitting

Self-check each finding.

---

## Step 7 — Run all validation scripts

```bash
python scripts/validate_coverage.py <run-dir>/agents/conventions.coverage.json
```

---

## Step 8 — Self-attest Definition of Done

Read `references/DOD.md`, fill attestation, write to `<run-dir>/agents/conventions.dod.json`.
