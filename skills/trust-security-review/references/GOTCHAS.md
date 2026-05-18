# GOTCHAS — trust-security-review

> Environment-specific facts that defy reasonable assumptions. Load when you encounter an ambiguous case.

This file follows the **gotchas pattern** recommended by [agentskills.io best practices](https://agentskills.io/skill-creation/best-practices#gotchas-sections). These are concrete corrections to mistakes you will make without being told otherwise.

---

## Diff context

### Gotcha: the diff shows changes, not the whole file

When a rule needs whole-file context (e.g. "every API endpoint must have auth check"), the diff alone is insufficient. Read the full file from `<run-dir>/diff.context/<file-path>` — the orchestrator pre-loads full file contents for files in the diff.

```python
# WRONG — reasoning only from diff hunks
hunks = diff.get_hunks("src/api/users.ts")  # may miss auth middleware applied elsewhere

# RIGHT — also read full file when rule requires whole-file analysis
full_file = read_text(f"<run-dir>/diff.context/src/api/users.ts")
```

### Gotcha: line numbers refer to the NEW version

After a diff, line numbers in your finding must refer to the **post-change** state. The diff format shows both old and new — always use new.

### Gotcha: a "removed" line is not actionable

If a line was removed (`-` prefix in the diff), don't emit findings about it. The vulnerability is gone. Focus on `+` and unchanged context lines.

---

## Evidence quote pitfalls

### Gotcha: backticks and template literals

When the code uses template literals, the backticks are part of the literal evidence. Don't strip them.

```ts
// Original code:
const q = `SELECT * FROM users WHERE id=${userId}`;

// ❌ WRONG quote (stripped backticks):
"const q = SELECT * FROM users WHERE id=${userId};"

// ✅ RIGHT quote:
"const q = `SELECT * FROM users WHERE id=${userId}`;"
```

### Gotcha: trailing whitespace and tabs

Some files use tabs, some use spaces. Copy-paste the exact whitespace. If you "clean up" indentation, the meta-reviewer will fail the finding.

### Gotcha: multi-line statements

A single statement can span multiple lines. Capture all relevant lines:

```ts
// Original (3 lines):
const result = await db.query(
  `SELECT * FROM users WHERE email='${email}'`,
  { timeout: 5000 }
);

// Quote MUST include all 3 lines as written.
```

### Gotcha: Unicode and special chars

Some codebases have non-ASCII characters in comments or strings (acentos, emojis). Preserve them. Don't normalize.

---

## Confidence calibration

### Gotcha: pattern-matching is not enough

If you see `db.query(${...})`, this looks like SQLi — but if the surrounding context shows `${...}` is itself a validated constant or whitelisted enum, the risk drops dramatically. In these cases:

- Drop confidence below 0.80 → don't emit
- OR investigate the source of the interpolated value

When in doubt, **don't emit**. Precision > recall.

### Gotcha: framework-level protections

Many frameworks (TypeORM, Prisma, Django ORM, ActiveRecord) automatically parameterize. If you see `repository.findOne({ where: { email } })`, this is NOT SQLi — the ORM handles it.

Before emitting an injection finding, ask: does this code use a raw query interface or a parameterizing ORM? If unsure, drop confidence.

### Gotcha: legacy patterns intentionally kept

Sometimes a project has documented exceptions (e.g. "this query is admin-only and email is server-controlled"). The grounding might have an ADR explaining this. Always check `07-adrs/` before emitting findings in suspicious code patterns.

---

## Coverage matrix edge cases

### Gotcha: empty domain

If the diff has 12 files but **none** match your domain patterns:

- `files_in_domain_total: 0`
- `files_in_domain_evaluated: 0`
- `files_in_domain_evaluated_pct: 100` ← still 100, by convention

This is OK. You evaluated everything that was in your domain (which was nothing).

### Gotcha: a rule that's universally N/A

If a rule is `not_applicable` for every file in the diff, you still need to record that in the coverage matrix. Don't omit. The matrix proves you considered the rule and decided it doesn't apply.

### Gotcha: same file matches multiple file_patterns

If your config has both `**/*.ts` and `**/auth/*`, a file like `src/auth/login.ts` matches both. Evaluate it once, not twice.

### Gotcha: generated files

Files like `*.generated.ts`, `*.pb.go`, schema migrations from tooling — these are typically excluded by `path_filters.ignore` in the target. If they appear in your domain anyway, mark every rule as N/A with reason "generated file".

---

## Severity vs confidence confusion

### Gotcha: critical bugs you're unsure about

You can have a `severity: critical` finding with `confidence: 0.75`. The bug **would be** critical if it's real, but you're not sure.

In this case: **do not emit**. The Precision Gate would silence it. Better to log internally and let the dev investigate manually.

### Gotcha: certain low-severity findings

You can be 99% sure about a missing security header (`severity: low`, `confidence: 0.99`). Emit it. Low-but-certain findings still add value when batched.

---

## Cross-cutting issues

### Gotcha: the bug is real but in a file not yours

Example: you find a SQL injection in `src/utils/db-helper.ts`, but that file isn't touched by the diff. The vulnerability exists, but the developer isn't introducing it in this PR.

Decision tree:
- Is the file in the diff? No → don't report. Out of scope for THIS PR review.
- Is the file in the diff but only deleted lines? Same → don't report.
- The vulnerability is being newly introduced or modified in this PR? Yes → report.

Reporting pre-existing bugs in PR review creates noise. The team should run TRUST on the full repo periodically for that.

### Gotcha: rule overlap with another agent

Sometimes a finding could be classified as security OR conventions OR contracts. Example: leaking internal error details in API response.

Rule of thumb:
- If the leak is exploitable (auth tokens, stack traces with secrets) → security
- If it's just style/UX (verbose 500 messages) → conventions

When unsure, check which agent's checklist mentions the specific rule. Whichever has it, that agent reports.

### Gotcha: test files

`*.test.ts`, `*.spec.ts`, `__tests__/**` — these often contain "vulnerabilities" by design (hardcoded test secrets, raw SQL for testing, etc).

- Default: skip test files for security rules
- Exception: if a rule explicitly says "applies to all files including tests" in the checklist, evaluate them

When in doubt, mark as N/A with reason "test file, not production code".

---

## Output format gotchas

### Gotcha: JSON in evidence_quote

When the code itself contains JSON or quotes, escape carefully in the JSON output:

```json
// Original code: const x = '{"key":"value"}';
// Wrong (broken JSON):
"evidence_quote": "const x = '{"key":"value"}';"

// Right (escaped):
"evidence_quote": "const x = '{\"key\":\"value\"}';"
```

### Gotcha: very long lines

Some files have minified or generated lines that are thousands of chars long. If a violation happens in a long line, quote ONLY the relevant span (use a substring), but make sure that substring is still literal and unique to the file.

If the substring isn't unique (e.g. very short), capture a few neighboring chars to make it locatable.

---

## When you're tempted to be helpful

### Gotcha: don't suggest features

Your role is to enforce rules from the checklist. If you notice "this code could be improved by adding X", but X isn't in the checklist:

- Don't emit a finding
- Don't add a "side note" comment

Stay in scope. Suggesting improvements outside the rules dilutes signal.

### Gotcha: don't speculate about user intent

"The developer probably meant to..." — never. Report what the code DOES, not what you think the developer intended.

### Gotcha: don't blame past PRs

"This issue was introduced in commit X..." — out of scope. Report on the current state of the diff, not history.

---

## Second pass specifically

When the Second Pass phase runs, you'll be asked to justify hunks you **didn't** report. Common temptations:

### Gotcha: "I didn't report because it's not my domain"

Valid reason. Use `reason_not_reported: "Out of domain: this is a performance concern, not security"`.

### Gotcha: "I didn't report because confidence was low"

Valid reason. Use `reason_not_reported: "Pattern matched a security rule but confidence was 0.65 — uncertain about validated input upstream"`.

### Gotcha: "I didn't report because it's a known pattern in this project"

Valid reason **only if** documented in grounding/ADRs. Cite the ADR. Otherwise, suspicious — you're using "general knowledge".

### Gotcha: "I forgot to look at this hunk"

NOT valid. This is exactly what Second Pass catches. Go back, evaluate the hunk properly, and add to either findings or non-findings.

---

**Remember:** these gotchas exist because real executions taught us they're easy to get wrong. Trust them.
