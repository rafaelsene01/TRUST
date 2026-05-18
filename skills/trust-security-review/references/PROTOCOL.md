# PROTOCOL — trust-security-review

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

Read the following files from the setup repo's `grounding/` (paths from `trust.config.yaml`):

- `01-architecture.md` — to understand module boundaries
- `02-domain-glossary.md` — to use correct entity names
- `05-conventions.md` — to know error handling and naming patterns
- `06-security-policy.md` — **your primary source of truth**
- `07-adrs/` — relevant ADRs that may override default rules

Index the sections by anchor (e.g. `06-security-policy.md#input-validation`). You will reference these as `rule_source` in findings.

If any required doc is missing → **halt**.

---

## Step 2 — Load checklist

Read `checklists/security.checklist.md` from the setup repo. Parse it into a structured list:

```json
[
  {
    "rule_id": "SEC-001",
    "title": "Secrets must not appear in source code",
    "source": "06-security-policy.md#secrets",
    "severity_default": "critical"
  },
  ...
]
```

Each rule in the checklist must have:
- A unique `rule_id`
- A non-empty `title`
- A valid `source` pointing to a section in grounding

If any rule lacks any of these → **halt**.

---

## Step 3 — Inventory diff files in domain

From the diff, list every file that matches the agent's `file_patterns` (defined in `trust.config.yaml > agents.security`):

```python
files_in_domain = [f for f in diff.files if matches_any(f.path, file_patterns)]
```

For the security agent, `file_patterns: ["**/*"]` — security looks at everything.

Record:
- `files_in_diff_total` — all files in diff
- `files_in_domain_total` — files this agent will evaluate
- `files_in_domain_evaluated` — should equal `files_in_domain_total` at the end

---

## Step 4 — Build the coverage matrix

This is the **central artifact** of your execution. For every `(rule × file)` pair, produce a verdict.

Verdicts:

- `compliant` — file does NOT violate the rule
- `violation` — file violates the rule → emit a finding
- `not_applicable` — rule doesn't apply to this file (requires justification)

**Rules for `not_applicable`:**
- You MUST provide a one-sentence justification
- N/A is not an escape hatch — only use when the rule genuinely doesn't apply
- If unsure between N/A and compliant, prefer compliant

**Example coverage entry:**

```json
{
  "rule_id": "SEC-007",
  "title": "Parameterized SQL queries",
  "files_checked": [
    "src/auth/login.ts",
    "src/auth/session.ts",
    "src/api/users.ts"
  ],
  "verdicts": [
    { "file": "src/auth/login.ts", "verdict": "violation" },
    { "file": "src/auth/session.ts", "verdict": "compliant" },
    { "file": "src/api/users.ts", "verdict": "not_applicable", "reason": "File contains no DB access" }
  ]
}
```

---

## Step 5 — Generate findings from violations

For every `violation` verdict in the coverage matrix, produce a finding using the schema in `references/FINDING_FORMAT.md`.

Critical reminders during this step:

1. `evidence_quote` MUST be literal — copy-paste from the diff, never paraphrase
2. `confidence` < 0.80 means **skip emitting** — the finding will be silenced anyway
3. Same problem in multiple files = multiple findings, not one consolidated
4. `why_it_matters` must reference the **project context**, not generic consequences

---

## Step 6 — Validate findings before emitting

Before writing `security.findings.json`, run these self-checks:

```python
for finding in findings:
    assert finding.rule_id is not None, "missing rule_id"
    assert finding.rule_source is not None, "missing rule_source"
    assert finding.evidence_quote is not None, "missing evidence_quote"
    assert 0.0 <= finding.confidence <= 1.0, "invalid confidence"

    # Critical: evidence quote must exist literally in the diff
    assert finding.evidence_quote in diff.get_file_content(finding.file), \
        f"evidence_quote is not literal in {finding.file}"
```

Any failure → fix or remove the finding. Do not emit invalid findings.

---

## Step 7 — Run all validation scripts before declaring done

Run the following scripts **in this exact order**. Stop at the first failure and fix
the issue before continuing. Do not skip or reorder them.

```bash
# 1. Confirm the checklist is well-formed (required before coverage matrix is final)
python scripts/parse_checklist.py <setup-repo>/checklists/security.checklist.md \
  --output /tmp/trust-rules.json

# 2. Confirm 100% rule × file coverage
python scripts/validate_coverage.py <run-dir>/agents/security.coverage.json

# 3. Confirm all evidence_quote values are literal (character-by-character) in the diff
python scripts/check_evidence_literal.py \
  <run-dir>/agents/security.findings.json \
  <run-dir>/diff.patch

# 4. Confirm all rule_source values resolve to real sections in grounding
python scripts/check_rule_source.py \
  <run-dir>/agents/security.findings.json \
  <setup-repo>/grounding/

# 5. Final gate: confirm the DoD attestation block is complete and correct
python scripts/validate_dod_attestation.py \
  <run-dir>/agents/security.dod.json
```

**All scripts must exit with code `0`.** If any exits with `1`, the script output
tells you exactly what to fix. Do NOT declare done until all 5 pass.

---

## Step 8 — Self-attest Definition of Done

Read `references/DOD.md` and fill the attestation block, then write it to
`<run-dir>/agents/security.dod.json`. Use `assets/dod-attestation-template.json`
as the structural reference.

Every boolean in `dod.findings.*` must be `true`.
Every `*_pct` field in `dod.coverage.*` must be `100`.
`dod.self_check_passed` must be `true` and `dod.halt_required` must be `false`.

If any criterion fails: set `self_check_passed: false`, write the partial output
as-is, and return a structured error. The orchestrator decides whether to HALT —
your job is to attest honestly.

---

## Common execution mistakes to avoid

- **Treating diff context as project context.** The diff shows changes, but you also need surrounding code from the file. Read the full file when needed.
- **Reporting on unchanged code.** You evaluate the diff. Untouched code is out of scope unless a rule explicitly requires whole-file review.
- **Confusing `severity` with `confidence`.** A finding can be critical with low confidence (don't emit). A finding can be low severity with high confidence (emit).
- **Skipping the coverage matrix and going straight to findings.** This breaks Pilar 2 (cobertura mensurável). Always build the matrix first.

---

**Next:** load `references/FINDING_FORMAT.md` to see the exact JSON schema for findings.
