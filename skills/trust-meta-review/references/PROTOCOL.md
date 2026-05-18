# PROTOCOL — trust-meta-review

> Step-by-step execution for the Meta-Review anti-hallucination phase. Load before starting.

---

## Step 0 — Verify inputs

Confirm all required inputs exist:

- `<run-dir>/diff.patch` — the actual diff
- `<run-dir>/agents/<agent>.findings.json` — for each agent that ran
- `<run-dir>/agents/<agent>.coverage.json` — for cross-checking rule_source
- Setup repo `grounding/` directory — for resolving rule_source anchors

If any file is missing → halt with a structured error.

---

## Step 1 — Load all findings

Collect all findings from all agent `findings.json` files into a single list.
For each finding, record which agent emitted it.

---

## Step 2 — Check 1: evidence_quote is literal

For each finding:

```python
diff_content = read_file("<run-dir>/diff.patch")
assert finding.evidence_quote in diff_content, "not literal"
```

If the quote is NOT a substring of the full diff content → mark as hallucination.
Record the nearest similar string (first 30 chars of the quote) as a diagnostic hint.

---

## Step 3 — Check 2: rule_source resolves

For each finding:

1. Parse `rule_source` as `<source-id>:<path>#<anchor>`
2. Locate the file in `<setup-repo>/grounding/`
3. Extract headings as anchors (lowercase, hyphens)
4. Confirm the requested anchor exists

If the file does not exist or the anchor is not found → mark as hallucination.

---

## Step 4 — Check 3: claim is supported by evidence

For each finding, verify the claim does not assert facts that are not visible
in the `evidence_quote`:

- The claim can EXPLAIN the evidence (why it's a problem)
- The claim CANNOT assert facts about other files or invisible code
- The claim CANNOT state that an attack "has occurred" — only that the vulnerability exists

Examples of unsupported claims:
- `"The attacker used this SQLi to extract the users table"` — speculation beyond the diff
- `"This function is called from the admin panel without auth"` — refers to invisible code

Mark as hallucination with failure_reason "claim exceeds evidence scope".

---

## Step 5 — Check 4: confidence ≥ 0.80

For each finding:

```python
assert finding.confidence >= 0.80
```

If below threshold → the agent should not have emitted it. Mark as hallucination.

---

## Step 6 — Check 5: rule_id exists in checklist

For each finding, confirm `rule_id` exists as a declared rule in the agent's checklist.
Cross-reference against `<setup-repo>/checklists/<agent>.checklist.md`.

If the rule_id was invented (not in the checklist) → mark as hallucination.

---

## Step 7 — Write meta-review report

Write `<run-dir>/meta-review/report.json` using the schema from `SKILL.md`.

Set `halt_required = (findings_failed > 0)`.

For each failed finding:
- Remove it from the findings that will be passed to the Precision Gate
- Include it in the `hallucinations` array with full diagnostic detail

---

## Step 8 — Return result to orchestrator

If `halt_required: false` → pass the surviving findings to Phase 4 (Precision Gate).

If `halt_required: true` → orchestrator HALTS. The developer receives a report
showing which findings were hallucinated and why, so the agent can be retrained/adjusted.

---

## Common mistakes to avoid

- **Semantic similarity ≠ literal match**: "same meaning" is not enough. The quote must be a
  character-by-character substring of the diff.
- **Being too strict on claim scope**: the claim CAN reference the grounding docs and
  explain why the pattern is dangerous — that's not speculation. Only flag claims that
  assert facts about invisible code or external actors.
- **Removing valid findings to reduce halts**: every hallucination MUST be removed and
  reported, even if that reduces the finding count to zero. Accuracy > quantity.
