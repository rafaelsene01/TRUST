# GOTCHAS — trust-contracts-review

> Edge cases specific to contract review. Load when you encounter ambiguous cases.

---

## Breaking change detection

### Gotcha: additive changes are NOT breaking
Adding optional fields to a response, or adding new optional request fields, is
generally not a breaking change. Only report a violation if:
- A field is **removed** or **renamed**
- A field's **type** is narrowed or changed
- A **required** field is added without a default
- An **endpoint path or method** is changed

### Gotcha: TypeScript type aliases vs structural changes
If a DTO changes its type from `UserResponse` to `UserDetailResponse`, this is
NOT automatically a breaking change. You must inspect what changed in the type
definition itself. If `UserDetailResponse` is a superset, it's non-breaking.
Lower confidence if you cannot see the type definition in the diff.

### Gotcha: internal vs public APIs
Only flag breaking changes on **public** APIs. Check `03-api-contracts.md` or
`01-architecture.md` to determine which endpoints are internal (service-to-service,
admin-only, or not documented in the contract spec). Internal APIs may have
different versioning rules.

---

## Schema detection

### Gotcha: implicit schema through validation middleware
Many frameworks define request schemas through validation middleware (Joi, Zod,
class-validator), not DTO classes. A breaking schema change may appear in a
middleware file, not a DTO. Check both.

### Gotcha: GraphQL schema files vs resolvers
Breaking changes to GraphQL can happen in:
1. The `.graphql` schema file (field removal, type change)
2. The resolver (return type changes, field omission)
Both require coverage — they're separate files in your domain.

---

## Versioning

### Gotcha: URL versioning vs header versioning
Some projects version via URL (`/v1/users`), others via Accept header
(`Accept: application/vnd.api+json;version=2`), others via query param.
Always check `03-api-contracts.md#versioning` for the project's strategy
before flagging a missing version bump.

### Gotcha: semver vs date-based versioning
The project may not use `/v1/`, `/v2/` URL versioning at all. Some use
date-based versions (`2026-05-18`) or feature flags. Understand the project's
strategy before recommending a "version bump".

---

## Common false positives

### Gotcha: CHANGELOG or migration guide catches the break
Sometimes a PR includes a breaking change AND a migration guide or client update
in the same diff. If the break is documented and mitigated in the same PR,
lower confidence (or mark as N/A if the checklist explicitly allows this).

### Gotcha: shared schema updated by the schema owner
If the PR author is updating a schema they own, and the change is additive,
this is often intentional and pre-coordinated. Still report if the rule is
violated, but reflect this context in `false_positive_risk: medium`.
