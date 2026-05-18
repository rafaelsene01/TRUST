# SECOND PASS — trust-security-review

> Protocol for the Second Pass phase. Load this document when the orchestrator
> reaches Phase 3, after the primary findings have been generated and validated.

---

## What is the Second Pass and why it exists

The primary review (Steps 1-6 of PROTOCOL.md) focuses on **finding violations**.
An LLM under that pressure tends to skip hunks that look safe at first glance.
The Second Pass forces accountability: **every hunk must be explicitly accounted for**,
either as a finding or as a cleared non-finding with a written reason.

This implements Pilar 3 (combate à preguiça do LLM). A hunk that is neither a finding
nor explicitly cleared is called **unaccounted** — and triggers an immediate HALT.

The DoD for Second Pass is simple:

```
hunks_unaccounted == 0
```

---

## Step-by-step protocol

### Step SP-1 — Enumerate all hunks in domain

A **hunk** is each `@@` block in the unified diff. Count them by file, then filter
to files in this agent's domain (`file_patterns`).

For the security agent, `file_patterns: ["**/*"]` — all files in the diff are in scope.

For each `@@` block, record:
- `file` — the file path from the `---`/`+++` header above it
- `line_start` — the new-file start line from the `@@ -old +new @@` header
- `line_end` — `line_start + hunk_line_count - 1`
- `hunk_id` — formatted as `<file>:<line_start>-<line_end>`

Build a flat list: `all_hunks: list[hunk_id]`.

**Example from `feat-PAY-123.patch`:**

```diff
--- a/src/auth/login.ts
+++ b/src/auth/login.ts
@@ -40,8 +40,10 @@ export async function login(req: Request): Promise<Response> {
   const email = req.body.email;
-  const user = await db.query(`SELECT * FROM users WHERE email='${email}'`);
+  const result = await db.query(`SELECT * FROM users WHERE email='${email}'`);
```

This yields:
```
hunk_id: "src/auth/login.ts:40-49"
file: "src/auth/login.ts"
line_start: 40
line_end: 49
```

---

### Step SP-2 — Classify each hunk

For every hunk in `all_hunks`, decide its status:

| Status | Meaning |
|--------|---------|
| `with_finding` | At least one finding was emitted for this hunk |
| `cleared` | No finding, but a written reason is provided in `non_findings` |

A hunk is `with_finding` when its `hunk_id` overlaps with the line range of an
emitted finding (same file, `line_start` within finding's range).

Every other hunk MUST be `cleared`.

---

### Step SP-3 — Write the Second Pass report

Fill `assets/second-pass-template.json`:

```json
{
  "agent": "security",
  "run_id": "<from run-manifest>",
  "hunks_total": <count of all_hunks>,
  "hunks_with_finding": <count of 'with_finding' hunks>,
  "hunks_explicitly_cleared": <count of 'cleared' hunks>,
  "hunks_unaccounted": 0,
  "non_findings": [ ... one entry per cleared hunk ... ]
}
```

Verify: `hunks_with_finding + hunks_explicitly_cleared == hunks_total`.

If the numbers don't add up, there are unaccounted hunks. Do not falsify the count.
Instead, go back to Step SP-2 and clear the missing hunks.

---

### Step SP-4 — Write reasons for cleared hunks

For each cleared hunk, write a `reason_not_reported` using the standard vocabulary
from `assets/non-finding-reasons.md`. Pick the closest category.

**Mandatory:** the reason must be non-empty and at least 10 characters.
**Forbidden:** `"Compliant"`, `"OK"`, `"No issues"`, or any non-explanation.

---

### Step SP-5 — Verify the DoD

After writing the report, confirm:

```python
assert report["hunks_unaccounted"] == 0
assert report["hunks_with_finding"] + report["hunks_explicitly_cleared"] == report["hunks_total"]
assert all(len(nf["reason_not_reported"]) >= 10 for nf in report["non_findings"])
```

Any assertion failure → fix the report before proceeding. Do not declare the Second
Pass done with `hunks_unaccounted > 0`.

---

## Complete examples

### Example A — Hunk that became a finding

```json
{
  "hunk_id": "src/auth/login.ts:40-49",
  "file": "src/auth/login.ts",
  "line_start": 40,
  "line_end": 49
}
```

This hunk was classified `with_finding` because SEC-007 was emitted for line 42.
It does **not** appear in `non_findings`. It is counted in `hunks_with_finding`.

---

### Example B — Hunk cleared as "out of domain"

```json
{
  "hunk_id": "src/utils/date-formatter.ts:10-24",
  "file": "src/utils/date-formatter.ts",
  "line_start": 10,
  "line_end": 24,
  "reason_not_reported": "Out of domain: changes are purely date formatting logic with no security-relevant surface (no input validation, no DB access, no auth)."
}
```

---

### Example C — Hunk cleared as "confidence below threshold"

```json
{
  "hunk_id": "src/api/users.ts:88-102",
  "file": "src/api/users.ts",
  "line_start": 88,
  "line_end": 102,
  "reason_not_reported": "Confidence below threshold: the query builder method buildUserFilter may or may not use parameterization internally; confidence 0.65 is below the 0.80 minimum. Not emitted."
}
```

---

## Edge cases

**Hunk in a test file:** use category "Test file" from `non-finding-reasons.md`.
Do not skip — even test files must be accounted for.

**Hunk in auto-generated file:** use "Generated code". Still counts toward total.

**Same rule found in multiple hunks of the same file:** each hunk is a separate entry.
Do not collapse — one finding per hunk is expected.

**@@ header with complex ranges (`@@ -0,0 +1,30 @@`):** `line_start = 1`, `line_end = 30`.
Use the new-file range (the `+` side), not the old-file range.

**Binary or non-text files:** classify as "No relevant surface in file" with reason
`"Binary/non-text file: not analyzable by static review."` Count toward total.

---

## Output file

Write to: `<run-dir>/agents/security.second-pass.json`

The orchestrator reads `hunks_unaccounted` first. If non-zero → HALT.
