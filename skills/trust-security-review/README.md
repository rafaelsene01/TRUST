# trust-security-review

Security review specialist for the TRUST framework. Reviews PR diffs for violations
of the project's own security rules — no generic knowledge, no hallucination.

---

## Artifacts

| Artifact | Purpose | When to load |
|---|---|---|
| `SKILL.md` | Entry point: scope, golden rules, 3 end-to-end examples | Once, at session start |
| `references/PROTOCOL.md` | 8-step execution protocol | Before touching the diff |
| `references/FINDING_FORMAT.md` | JSON schema for findings, field-by-field rules | Before emitting the first finding |
| `references/DOD.md` | Definition of Done + self-attestation block | Before declaring done |
| `references/GOTCHAS.md` | Edge cases and ambiguous patterns | When encountering an unclear case |
| `references/SECOND_PASS.md` | Second Pass protocol (Phase 3) | When orchestrator enters Phase 3 |
| `scripts/validate_coverage.py` | Confirms 100% rule × file coverage | Run at Step 7 (see PROTOCOL.md) |
| `scripts/check_evidence_literal.py` | Confirms all evidence_quote values are literal | Run at Step 7 |
| `scripts/parse_checklist.py` | Parses checklist.md into structured JSON | Run at Step 7 |
| `scripts/validate_dod_attestation.py` | Final gate — validates the DoD JSON block | Run at Step 7 |
| `scripts/check_rule_source.py` | Confirms all rule_source anchors resolve | Run at Step 7 |
| `assets/finding-template.json` | JSON Schema for a single finding | Reference when writing findings |
| `assets/coverage-template.json` | JSON Schema for the coverage matrix | Reference when building coverage |
| `assets/dod-attestation-template.json` | JSON Schema for the DoD attestation block | Reference when writing DoD |
| `assets/second-pass-template.json` | JSON Schema for the Second Pass report | Reference during Phase 3 |
| `assets/non-finding-reasons.md` | Standard vocabulary for cleared hunks | During Second Pass |

---

## Run isolated tests

```bash
python -m pytest tests/skills/test_security_skill.py -v
# Expected: 14 passed in < 5s
```

---

For the full skill specification format, see [`docs/04-skills-spec.md`](../../docs/04-skills-spec.md).
