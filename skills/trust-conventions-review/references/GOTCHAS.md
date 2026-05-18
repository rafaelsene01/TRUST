# GOTCHAS — trust-conventions-review

> Edge cases specific to conventions review. Load when you encounter ambiguous cases.

---

## Naming conventions

### Gotcha: the project may have multiple naming conventions by layer
Some projects use `PascalCase` for classes, `camelCase` for functions, `snake_case`
for DB fields, and `kebab-case` for files — all at the same time. Always check
`05-conventions.md` for layer-specific rules before flagging a naming violation.

### Gotcha: third-party library conventions override project conventions
When code interfaces with a third-party library (event names, config keys, API fields),
it often must match the library's naming scheme. A snake_case field that mirrors
a third-party API response is not a violation. Look for the `// 3rd-party format`
or similar comment as a hint.

---

## Logging

### Gotcha: one-off scripts vs production code
Logging rules typically apply to production service code, not CLI tools, build scripts,
or one-time migration utilities. If the file is clearly a script (not a service),
mark logging convention rules as N/A.

### Gotcha: test files often use console.log intentionally
Many projects permit `console.log` in test files for debugging output. Check if
`05-conventions.md#logging` explicitly applies to test files, or only to production code.

---

## Error handling

### Gotcha: intentional error swallowing with a comment
Some places in code swallow errors intentionally and document why:
```typescript
try { cleanupTempFile(path); } catch { /* non-critical, best-effort */ }
```
This might violate a "don't swallow errors" convention, but the comment signals
intent. Lower confidence — include in non-findings with reason "ADR exception or
documented intentional swallow".

---

## Complexity limits

### Gotcha: the function body is large but has a single responsibility
Sometimes a long function is acceptable when it's a data transformation pipeline or
a state machine with explicit cases. Don't flag complexity purely by line count —
confirm the rule's intent in `05-conventions.md`.

---

## Common false positives

### Gotcha: grandfathered code patterns
Sometimes an old pattern exists in untouched code adjacent to the diff.
You evaluate only `+` lines (new/changed code). Never report on unchanged
context lines that happen to violate a convention — that's pre-existing debt.
