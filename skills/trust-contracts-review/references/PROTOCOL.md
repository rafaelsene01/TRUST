# PROTOCOL — trust-contracts-review

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

- `03-api-contracts.md` — **your primary source of truth** (versioning, breaking changes, schema rules)
- `01-architecture.md` — to understand service boundaries and API layer responsibilities
- `02-domain-glossary.md` — to use correct entity and field names
- `07-adrs/` — relevant ADRs that may document intentional contract exceptions

Index sections by anchor. You will reference these as `rule_source` in findings.

If any required doc is missing → **halt**.

---

## Step 2 — Load checklist

Read `checklists/contracts.checklist.md` from the setup repo. Parse it into a structured list (each rule needs `rule_id`, `title`, `source` with `#anchor`).

If any rule lacks required fields → **halt**.

---

## Step 3 — Inventory diff files in domain

Files in the contracts domain: route files, controller files, handler files, OpenAPI/Swagger specs, GraphQL schema files, protobuf files, DTO/schema definition files, and any file that defines or modifies a public API surface.

```
file_patterns: ["**/routes/**", "**/controllers/**", "**/handlers/**",
                "**/*.graphql", "**/*.proto", "**/dto/**", "**/schema/**",
                "**/openapi/**", "**/swagger/**"]
```

For each file in the diff, determine if it's in your domain. Record:
- `files_in_diff_total` — all files
- `files_in_domain_total` — files you'll evaluate
- `files_in_domain_evaluated` — must equal total at end

---

## Step 4 — Build the coverage matrix

For every `(rule × file)` pair, produce a verdict: `compliant`, `violation`, or `not_applicable` (with mandatory justification).

**Key question per rule:** does this change introduce or touch a public API surface that could violate the rule?

For breaking change rules specifically: compare the BEFORE and AFTER state of the signature/schema. The diff shows both — use the context lines (`-` and `+`) to assess the delta.

---

## Step 5 — Generate findings from violations

For every `violation` verdict, produce a finding using `references/FINDING_FORMAT.md`.

Critical reminders:
1. `evidence_quote` MUST be literal copy-paste from the diff (+ lines or unchanged context)
2. `confidence < 0.80` means **skip**
3. `false_positive_risk` is often `medium` for contract findings — many apparent breaking changes are actually additive. Be honest.

---

## Step 6 — Validate findings before emitting

Self-check each finding:
- `rule_id` exists in the checklist
- `rule_source` resolves to a real grounding section
- `evidence_quote` is a literal substring of the diff
- `confidence >= 0.80`
- `claim` is factual, not hedged

---

## Step 7 — Run all validation scripts

```bash
python scripts/validate_coverage.py <run-dir>/agents/contracts.coverage.json
```

Exit 0 to proceed. Any exit 1 → fix before declaring done.

---

## Step 8 — Self-attest Definition of Done

Read `references/DOD.md`, fill the attestation block, write to `<run-dir>/agents/contracts.dod.json`.

Every `_pct` must be 100. Every boolean in `findings.*` must be `true`.
