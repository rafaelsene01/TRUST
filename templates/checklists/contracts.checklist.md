# Contracts Checklist

> Source of truth: `grounding/03-api-contracts.md`
> Maintained by: {{TEAM_NAME}}
> Last reviewed: {{DATE}}

Each rule must have a unique `rule_id` in format `CON-XXX`, a `source` pointing to
a section in the contracts grounding doc, and a clear, testable `title`.

---

### CON-001 — No removal of existing response fields
**Source:** `03-api-contracts.md#breaking-changes`
**Severity default:** critical

Fields present in a response schema must never be removed without a version bump.
Removing a field breaks all existing clients that depend on it.

**Applies to:** controller/handler files, DTO/response schema files

---

### CON-002 — No addition of required request fields without default
**Source:** `03-api-contracts.md#breaking-changes`
**Severity default:** critical

Adding a required (non-optional) field to an existing request schema breaks callers
that do not send the new field. Provide a default or make the field optional.

**Applies to:** DTO/request schema files, route validation middleware

---

### CON-003 — No change to existing field types
**Source:** `03-api-contracts.md#breaking-changes`
**Severity default:** critical

Changing a field's type (e.g. `string` → `number`, `object` → `array`) is a
breaking change regardless of semantic equivalence.

**Applies to:** DTO files, schema files, protobuf definitions

---

### CON-004 — No endpoint path or method changes without versioning
**Source:** `03-api-contracts.md#versioning`
**Severity default:** critical

Renaming an endpoint path or changing its HTTP method is a breaking change.
Introduce a new versioned endpoint instead.

**Applies to:** route/router files, controller files

---

### CON-005 — Deprecated endpoints must include deprecation header or documentation
**Source:** `03-api-contracts.md#deprecation`
**Severity default:** high

When an endpoint is superseded by a new version, the old endpoint must emit
a `Deprecation` header (or equivalent) and reference the replacement.

**Applies to:** controller/handler files for deprecated routes

---

### CON-006 — Error response format must match project contract
**Source:** `03-api-contracts.md#error-format`
**Severity default:** high

All error responses must follow the documented format (e.g. `{error: string, code: string}`).
Ad-hoc error shapes break client error handling.

**Applies to:** controller/handler files, error middleware files

---

### CON-007 — Pagination contract must be preserved for list endpoints
**Source:** `03-api-contracts.md#pagination`
**Severity default:** high

List endpoints with an established pagination scheme must not change the
pagination mechanism (e.g. cursor → offset) or remove pagination params.

**Applies to:** controller files for list/collection endpoints

---

### CON-008 — New endpoints must be documented in the API contract spec
**Source:** `03-api-contracts.md#documentation`
**Severity default:** medium

New public endpoints must have a corresponding entry in the OpenAPI spec,
protobuf definition, or equivalent contract document before merging.

**Applies to:** new route/controller/handler files
