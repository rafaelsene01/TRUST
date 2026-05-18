# GOTCHAS — trust-tests-review

> Edge cases specific to test quality review. Load when you encounter ambiguous cases.

---

## Missing test coverage

### Gotcha: the tests exist but in a different diff hunk
A new function may have tests added in the same PR but in a different file not
visible in the current hunk. Before flagging TEST-001 (missing coverage), check
ALL files in the diff — not just the file with the new function.

### Gotcha: integration tests vs unit tests
If the project's policy requires integration tests (hitting real DB), a unit test
for the same function does NOT satisfy TEST-001. And vice versa. Read `05-conventions.md`
to understand what type of test is required before flagging.

### Gotcha: private functions don't require direct tests
Private/internal functions (unexported, or named with `_prefix`) are tested
indirectly through their callers. Don't flag missing tests for private functions.

---

## Conditional logic in tests

### Gotcha: test utilities vs test bodies
Conditional logic in shared test utility functions (helpers, factories, builders)
is acceptable. Only flag TEST-002 for logic inside the actual `it()`/`test()` body.

### Gotcha: parameterized tests
`test.each()`, `pytest.mark.parametrize`, `@ParameterizedTest` — these use
arrays/objects to run multiple cases, which may look like "data with conditions".
This is NOT a violation of TEST-002 as long as each parameterized run is unconditional.

---

## Mock usage

### Gotcha: mocking time and randomness is correct
Mocking `Date.now()`, `Math.random()`, `uuid()` is not mock overuse — it's
necessary for deterministic tests. Don't flag these as TEST-004 violations.

### Gotcha: external service mocks are expected
Mocking HTTP calls to external services (payment providers, email services) is
correct test practice. TEST-004 targets over-mocking of internal business logic,
not external infrastructure.

---

## Test descriptions

### Gotcha: BDD-style nested describes
`describe('UserService') > describe('login') > it('returns token')` — the full
behavior description is only legible when you read the full nesting. Don't flag
the inner `it` description in isolation without reading the describe hierarchy.

---

## Common false positives

### Gotcha: old tests not touched by the PR
You evaluate only `+` lines. Existing poorly-written tests that are NOT modified
in this PR are pre-existing debt. Don't flag them unless the PR modifies the test
in a way that introduces a new violation.
