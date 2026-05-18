# FINDING_FORMAT â€” trust-security-review

> Canonical schema for findings. Load this before emitting your first finding.

---

## Schema

```typescript
interface Finding {
  // Identification
  agent: "performance";
  rule_id: string;              // e.g. "PERF-001"
  rule_source: string;          // e.g. "in-setup:01-architecture.md#<section>"

  // Location
  file: string;                 // path relative to repo root
  line_start: number;           // 1-indexed, line in the NEW version of the diff
  line_end: number;             // inclusive

  // Classification
  severity: "critical" | "high" | "medium" | "low";
  confidence: number;           // 0.0 to 1.0, MUST be >= 0.80 to be emitted

  // Content
  claim: string;                // one-sentence factual description
  evidence_quote: string;       // LITERAL code from the diff
  why_it_matters: string;       // consequence in THIS project's context
  suggestion: string;           // proposed fix, ideally with code example

  // False positive tracking
  false_positive_risk: "low" | "medium" | "high";
  false_positive_reason: string | null;  // null if low; required if medium/high
}
```

---

## Field-by-field rules

### `agent`
Always `"performance"`. Never another agent's name.

### `rule_id`
Must match a `rule_id` declared in `checklists/security.checklist.md`. Format: "PERF-XXX" where XXX is a 3-digit number. Never invent rule IDs.

### `rule_source`
Format: `<source-id>:<path>#<anchor>`.

- `source-id` matches a source declared in `trust.config.yaml > grounding.sources`
- `path` is the relative path within that source
- `anchor` is a markdown heading anchor (lowercase, hyphens)

Example: `in-setup:01-architecture.md#<section>`

**Halt condition:** if you cannot resolve the rule_source to an actual document section, do not emit the finding.

### `file`
Relative path from the repo root, as it appears in the diff. Use forward slashes even on Windows.

### `line_start` and `line_end`
1-indexed lines in the **new** version (post-change) of the file. For single-line findings, `line_start == line_end`.

For multi-line findings (e.g. a function spanning 10 lines), report the smallest range that captures the violation. Don't span the entire function if the issue is in one line.

### `severity`
Reflects the **impact**, not the confidence:

- `critical` â€” exploitable vulnerability with immediate impact (SQLi, secret leak, auth bypass)
- `high` â€” serious risk but mitigated by other layers (weak crypto, missing rate limit)
- `medium` â€” defensive measure missing (verbose error messages, missing logging)
- `low` â€” style or hardening (could be better, not a real risk)

If the checklist rule defines a default severity, use it unless target overrides specify otherwise.

### `confidence`
Number from 0.0 to 1.0. Calibration guide:

| Range | Meaning |
| --- | --- |
| 0.95-1.00 | Textbook case, no reasonable counter-interpretation |
| 0.85-0.94 | Strong evidence, very unlikely false positive |
| 0.80-0.84 | Likely violation but some context could exonerate |
| < 0.80 | **DO NOT EMIT** â€” would be silenced anyway |

**Hard rule:** if you wrote `confidence < 0.80`, remove the finding before emitting.

### `claim`
One sentence. Factual. No hedging.

âœ… Good: `"User input concatenated directly into SQL query â€” SQL injection vulnerability."`
âŒ Bad: `"There might be a security issue with how the query is built."`

### `evidence_quote`
**The most critical field.** Must be literal copy-paste from the diff. Caractere a caractere.

- Preserve indentation
- Preserve quotes (backticks, single, double)
- Preserve semicolons
- Do NOT add `...` for truncation
- Do NOT collapse whitespace

The meta-reviewer will fail your finding if the quote is not literal.

If the violation requires multiple non-contiguous lines as evidence, emit **multiple findings**, one per location.

### `why_it_matters`
Must reference **this project's** context, not generic. Cite the rule_source explicitly.

âœ… Good: `"Per 01-architecture.md#<section>, this project requires parameterized queries in 100% of DB access (no exceptions). This line allows trivial SQLi against the user lookup endpoint."`

âŒ Bad: `"SQL injection is a common vulnerability that can lead to data breaches."`

### `suggestion`
Proposed fix. Code example preferred. Don't propose changes that violate other project rules â€” check the conventions doc if uncertain.

### `false_positive_risk`
Honest assessment of when this finding could be wrong:

- `low` â€” the violation is unambiguous (`false_positive_reason: null`)
- `medium` â€” context could exonerate (e.g. "if `email` is pre-validated upstream, this is safe")
- `high` â€” heuristic match, plausible but not certain

Findings with `medium` or `high` FP risk should also have lower `confidence`. They often won't pass the Precision Gate, which is fine.

### `false_positive_reason`
If `false_positive_risk` is `medium` or `high`, explain what circumstance would make this finding wrong. This helps the dev quickly assess.

âœ… `"If the `email` field is validated by a middleware layer (not visible in this diff), the concatenation might be safe â€” though parameterization is still preferred per project policy."`

---

## Complete example

```json
{
  "agent": "performance",
  "rule_id": "PERF-001",
  "rule_source": "in-setup:01-architecture.md#<section>",
  "file": "src/auth/login.ts",
  "line_start": 42,
  "line_end": 42,
  "severity": "critical",
  "confidence": 0.98,
  "claim": "User input concatenated directly into SQL query â€” classic SQL injection.",
  "evidence_quote": "const result = await db.query(`SELECT * FROM users WHERE email='${email}'`);",
  "why_it_matters": "Per 01-architecture.md#<section>, this project requires parameterized queries in 100% of DB access. This line allows trivial SQLi against the user lookup endpoint.",
  "suggestion": "const result = await db.query('SELECT * FROM users WHERE email = $1', [email]);",
  "false_positive_risk": "low",
  "false_positive_reason": null
}
```

---

## Validation checklist

Before adding a finding to `security.findings.json`, verify:

- [ ] All required fields are present
- [ ] `rule_id` exists in the checklist
- [ ] `rule_source` resolves to an actual grounding section
- [ ] `evidence_quote` is literal to the diff
- [ ] `confidence >= 0.80`
- [ ] `claim` is one factual sentence
- [ ] `why_it_matters` references project-specific context
- [ ] If `false_positive_risk != "low"`, `false_positive_reason` is non-null

---

**Next:** before declaring done, load `references/DOD.md` for the self-attestation block.

