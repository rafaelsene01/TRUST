# Tests Checklist

> Source of truth: `grounding/05-conventions.md` (testing section)
> Maintained by: {{TEAM_NAME}}
> Last reviewed: {{DATE}}

Each rule must have a unique `rule_id` in format `TEST-XXX`, a `source` pointing to
a section in the conventions/testing grounding doc, and a clear, testable `title`.

---

### TEST-001 — New public functions/endpoints must have corresponding tests
**Source:** `05-conventions.md#testing-policy`
**Severity default:** high

Every new exported function or API endpoint introduced in the PR must have at least
one happy-path test and one error-path test in the same PR.

**Applies to:** new production files (cross-checked against test files in the diff)

---

### TEST-002 — Test bodies must not contain conditional logic
**Source:** `05-conventions.md#testing-policy`
**Severity default:** medium

`if`, `for`, `while`, `switch` inside test bodies make tests non-deterministic.
Each test must exercise exactly one path. Split into separate `it()` blocks.

**Applies to:** test files

---

### TEST-003 — Test descriptions must describe behavior, not implementation
**Source:** `05-conventions.md#testing-policy`
**Severity default:** low

Test names like "calls repository" or "invokes method X" are brittle and
tell the reader nothing about intent. Names must describe the expected behavior:
"returns 404 when user does not exist", "sends confirmation email on success".

**Applies to:** test files

---

### TEST-004 — Tests must not mock all dependencies
**Source:** `05-conventions.md#testing-policy`
**Severity default:** medium

A test where every dependency is mocked tests nothing real. At least one
real dependency (usually the subject under test) must execute actual code.
Integration tests should hit real adapters.

**Applies to:** test files

---

### TEST-005 — Test fixtures must not share mutable state between tests
**Source:** `05-conventions.md#testing-policy`
**Severity default:** high

Shared mutable state between tests causes order-dependent failures that are
hard to reproduce. Each test must set up and tear down its own state.

**Applies to:** test files with shared `beforeAll`/`beforeEach` setups

---

### TEST-006 — Snapshot tests must have explicit assertions for critical fields
**Source:** `05-conventions.md#testing-policy`
**Severity default:** medium

Snapshot tests that capture an entire response object hide regressions in
critical fields. Critical fields (IDs, amounts, statuses) must have explicit
`expect(field).toBe(value)` assertions in addition to the snapshot.

**Applies to:** test files using snapshot testing
