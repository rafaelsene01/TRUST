# DOD — trust-security-review

> Definition of Done criteria and self-attestation block. Load before declaring done.

---

## Why strict DoD matters

The TRUST framework operates in **strict mode**. If your self-attestation fails any criterion, the orchestrator will HALT and preserve all artifacts for investigation.

Declaring done with incomplete work is **worse** than failing loudly. The dev can investigate a halt — but cannot recover from silent incompleteness.

---

## Self-attestation block (required at end of execution)

At the end of your execution, append the following block to your output (or write it as `<run-dir>/agents/security.dod.json`):

```json
{
  "agent": "security",
  "agent_version": "1.0.0",
  "run_id": "<from run-manifest>",
  "timestamp": "<ISO-8601>",
  "dod": {
    "grounding": {
      "loaded": true,
      "docs_read": [
        { "path": "06-security-policy.md", "sha256": "abc...", "sections_indexed": 12 },
        { "path": "05-conventions.md", "sha256": "def...", "sections_indexed": 8 }
      ],
      "missing_required": []
    },
    "checklist": {
      "loaded": true,
      "rules_in_checklist_total": 15,
      "rules_with_valid_source": 15
    },
    "coverage": {
      "diff_files_total": 12,
      "files_in_domain_total": 12,
      "files_in_domain_evaluated": 12,
      "files_in_domain_evaluated_pct": 100,
      "rules_evaluated_total": 15,
      "rules_evaluated_pct": 100,
      "coverage_matrix_complete": true,
      "not_applicable_with_justification_pct": 100
    },
    "findings": {
      "emitted": 3,
      "every_finding_has_rule_id": true,
      "every_finding_has_rule_source": true,
      "every_finding_has_evidence_quote": true,
      "every_finding_has_confidence": true,
      "every_finding_confidence_gte_080": true,
      "every_evidence_quote_literal": true
    },
    "self_check_passed": true,
    "halt_required": false
  }
}
```

---

## How to compute each field

### `grounding.loaded`
`true` if you successfully loaded all docs listed in `trust.config.yaml > grounding.required`. `false` otherwise → HALT.

### `grounding.docs_read[]`
For each loaded doc, record:
- `path` — relative path within the source
- `sha256` — hex hash of the file content (use `hashlib.sha256` in Python)
- `sections_indexed` — number of headings parsed

### `grounding.missing_required`
List of required docs that failed to load. **Must be empty** to declare done.

### `checklist.loaded`
`true` if `checklists/security.checklist.md` was parsed without errors.

### `checklist.rules_in_checklist_total`
Count of distinct `rule_id` declarations in the checklist.

### `checklist.rules_with_valid_source`
Count of rules whose `source` resolves to an existing section in grounding. Should equal `rules_in_checklist_total`.

### `coverage.files_in_domain_evaluated_pct`
Must be `100`. Formula:
```
pct = (files_in_domain_evaluated / files_in_domain_total) * 100
```
If you skipped any file in your domain for ANY reason, this drops below 100 → HALT.

### `coverage.rules_evaluated_pct`
Must be `100`. Every rule in the checklist must appear in the coverage matrix with at least one verdict per file in domain.

### `coverage.coverage_matrix_complete`
Boolean. `true` only if every `(rule × file)` pair has a verdict.

### `coverage.not_applicable_with_justification_pct`
For every verdict marked `not_applicable`, you must provide a `reason`. This field counts the percentage of N/A verdicts that have a non-empty reason. Must be `100`.

### `findings.every_*`
All boolean fields here must be `true`. They are mechanical checks:

```python
every_finding_has_rule_id = all(f.rule_id for f in findings)
every_finding_has_rule_source = all(f.rule_source for f in findings)
every_finding_has_evidence_quote = all(f.evidence_quote for f in findings)
every_finding_has_confidence = all(f.confidence is not None for f in findings)
every_finding_confidence_gte_080 = all(f.confidence >= 0.80 for f in findings)
```

### `findings.every_evidence_quote_literal`
The trickiest one. For each finding, verify the quote appears literally in the diff:

```python
for f in findings:
    file_content = diff.get_file_content(f.file)
    assert f.evidence_quote in file_content, f"non-literal quote in {f.file}"
```

Use the bundled script `scripts/check_evidence_literal.py` to automate this.

---

## The halt decision

After computing all fields:

```python
halt_required = (
    not dod["grounding"]["loaded"] or
    len(dod["grounding"]["missing_required"]) > 0 or
    not dod["checklist"]["loaded"] or
    dod["checklist"]["rules_with_valid_source"] < dod["checklist"]["rules_in_checklist_total"] or
    dod["coverage"]["files_in_domain_evaluated_pct"] < 100 or
    dod["coverage"]["rules_evaluated_pct"] < 100 or
    not dod["coverage"]["coverage_matrix_complete"] or
    dod["coverage"]["not_applicable_with_justification_pct"] < 100 or
    not dod["findings"]["every_finding_has_rule_id"] or
    not dod["findings"]["every_finding_has_rule_source"] or
    not dod["findings"]["every_finding_has_evidence_quote"] or
    not dod["findings"]["every_finding_has_confidence"] or
    not dod["findings"]["every_finding_confidence_gte_080"] or
    not dod["findings"]["every_evidence_quote_literal"]
)

self_check_passed = not halt_required
```

If `halt_required == true`:

1. Set `self_check_passed: false` in the DoD block
2. Write the partial output AS-IS to the run directory
3. Return a structured error to the orchestrator with the failed criterion

If `halt_required == false`:

1. Set `self_check_passed: true`
2. The orchestrator will proceed to Fase 3 (Second Pass)

---

## What the orchestrator does with your DoD

The orchestrator reads `security.dod.json` and:

- If `self_check_passed: false` → triggers HALT, preserves artifacts, creates `.trust-halt` marker
- If `self_check_passed: true` → proceeds to next phase

You are **not** the one who triggers HALT — the orchestrator is. Your job is to honestly attest.

---

## Common DoD failure modes

| Failure | Likely cause | Fix |
| --- | --- | --- |
| `files_in_domain_evaluated_pct: 87` | Skipped a file because it "looked safe" | Evaluate every file, mark as compliant if no issues |
| `rules_evaluated_pct: 93` | Skipped a rule because no file in diff seemed to need it | Mark as N/A with justification for each file |
| `every_evidence_quote_literal: false` | Paraphrased a long quote | Re-emit finding with literal quote; truncate to smallest meaningful range |
| `every_finding_confidence_gte_080: false` | Emitted a low-confidence finding | Remove the finding; it would be silenced anyway |
| `missing_required` non-empty | Grounding doc moved or renamed | Update path in `trust.config.yaml`, or restore the doc |

---

**Next:** if your execution is going off the rails, load `references/GOTCHAS.md`.
