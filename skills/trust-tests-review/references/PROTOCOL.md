# PROTOCOL — trust-tests-review

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

- `05-conventions.md` — **your primary source of truth** (testing policy, test naming, mock policy)
- `01-architecture.md` — to understand which layers require which test types
- `07-adrs/` — ADRs that document testing exceptions

Index sections by anchor.

If any required doc is missing → **halt**.

---

## Step 2 — Load checklist

Read `checklists/tests.checklist.md` from the setup repo. Parse into structured list.

If any rule lacks required fields → **halt**.

---

## Step 3 — Inventory diff files in domain

Test files AND production files (for coverage rules):

```
file_patterns_primary: ["**/*.test.*", "**/*.spec.*", "**/__tests__/**",
                         "**/*_test.*", "**/test_*.py", "**/*Test.java"]
file_patterns_production: ["**/*.ts", "**/*.js", "**/*.py", ...]
```

Evaluate test files for quality rules. Evaluate production files only if the checklist has a "new public function must have a test" rule — and only if test files are absent from the diff.

---

## Step 4 — Build the coverage matrix

For every `(rule × file)` pair, produce a verdict.

**Key assessment per rule type:**

- **No logic in tests** (e.g. TEST-002): look for `if`, `for`, `while`, `switch` inside test bodies (between `it()`/`test()` boundaries)
- **Test naming** (e.g. TEST-003): look for test descriptions that name implementation details ("calls repository") instead of behavior ("returns user when id is valid")
- **Mock overuse** (e.g. TEST-004): look for tests where every dependency is mocked, leaving nothing real to test
- **Missing coverage** (e.g. TEST-001): check if new public functions/endpoints in the diff have corresponding test additions

For TEST-001 (missing coverage): only flag if:
1. The grounding explicitly requires same-PR test coverage
2. The new function is clearly public/exported
3. No test file covering it appears in the diff

---

## Step 5 — Generate findings from violations

For every `violation` verdict, produce a finding using `references/FINDING_FORMAT.md`.

Severity calibration:
- `high`: missing test for a critical path (payment processing, auth, data mutation)
- `medium`: test quality issue (logic in tests, poor naming)
- `low`: style concern (verbose arrange/act, over-commenting)
- `critical`: **never** for test findings

---

## Step 6 — Validate findings before emitting

Self-check each finding.

---

## Step 7 — Run all validation scripts

```bash
python scripts/validate_coverage.py <run-dir>/agents/tests.coverage.json
```

---

## Step 8 — Self-attest Definition of Done

Read `references/DOD.md`, fill attestation, write to `<run-dir>/agents/tests.dod.json`.
