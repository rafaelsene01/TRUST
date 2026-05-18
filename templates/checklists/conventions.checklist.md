# Conventions Checklist

> Source of truth: `grounding/05-conventions.md`
> Maintained by: {{TEAM_NAME}}
> Last reviewed: {{DATE}}

Each rule must have a unique `rule_id` in format `CONV-XXX`, a `source` pointing to
a section in the conventions grounding doc, and a clear, testable `title`.

---

### CONV-001 — Error handling must use the project's error types
**Source:** `05-conventions.md#error-handling`
**Severity default:** medium

Errors must be instances of the project's documented error classes
(e.g. `AppError`, `DomainError`). Generic `Error` or string throws bypass
the error handling infrastructure (logging, tracking, HTTP mapping).

**Applies to:** service files, use-case files, domain files

---

### CONV-002 — All logging must use the project's Logger class
**Source:** `05-conventions.md#logging`
**Severity default:** medium

`console.log`, `console.error`, `print()`, or raw system loggers must not
be used in production code. All output must go through the project's Logger
to ensure structured output, correlation IDs, and log level control.

**Applies to:** all source files

---

### CONV-003 — File names must follow project naming convention
**Source:** `05-conventions.md#file-structure`
**Severity default:** low

File names must use the casing and suffix pattern defined in the project conventions
(e.g. `kebab-case.service.ts`, `snake_case_service.py`).

**Applies to:** all new files in the diff

---

### CONV-004 — Functions must not exceed the project's complexity limit
**Source:** `05-conventions.md#code-quality`
**Severity default:** medium

Functions that exceed the documented maximum lines/cyclomatic complexity must be
refactored. Check `05-conventions.md` for the project's specific thresholds.

**Applies to:** all source files

---

### CONV-005 — Async functions must use await, not .then() callbacks
**Source:** `05-conventions.md#async-patterns`
**Severity default:** low

If the project adopted async/await as the canonical pattern, `.then()` callback
chains must not be introduced in new code. Consistency reduces cognitive load.

**Applies to:** JavaScript/TypeScript files

---

### CONV-006 — Public module exports must match the documented barrel pattern
**Source:** `05-conventions.md#module-structure`
**Severity default:** low

New public exports must be re-exported through the module's index/barrel file,
not imported directly from internal files by consumers.

**Applies to:** index files, barrel files, new exported symbols
