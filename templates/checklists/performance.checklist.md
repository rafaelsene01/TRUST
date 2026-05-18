# Performance Checklist

> Source of truth: `grounding/01-architecture.md`
> Maintained by: {{TEAM_NAME}}
> Last reviewed: {{DATE}}

Each rule must have a unique `rule_id` in format `PERF-XXX`, a `source` pointing to
a section in the architecture/performance grounding doc, and a clear, testable `title`.

---

### PERF-001 — No database queries inside loops
**Source:** `01-architecture.md#performance-constraints`
**Severity default:** high

Database queries inside for/forEach/map/while loops produce N+1 query patterns.
Use batch fetching, eager loading, or aggregate queries instead.

**Applies to:** service files, repository files, resolver files

---

### PERF-002 — List queries must have a LIMIT or pagination
**Source:** `01-architecture.md#performance-constraints`
**Severity default:** high

Queries that fetch an unbounded result set will degrade as the dataset grows.
All list/find-all queries must include a LIMIT, pagination, or cursor parameter.

**Applies to:** service files, repository files, query files

---

### PERF-003 — External HTTP calls must have a timeout configured
**Source:** `01-architecture.md#performance-constraints`
**Severity default:** high

HTTP client calls without a timeout will block indefinitely on slow or unresponsive
external services. Every external call must declare a timeout matching the project's SLA.

**Applies to:** service files, HTTP client wrapper files

---

### PERF-004 — Synchronous file I/O must not be used in async request handlers
**Source:** `01-architecture.md#performance-constraints`
**Severity default:** high

Synchronous I/O calls (readFileSync, writeFileSync, etc.) block the event loop.
Use async equivalents in all request-handling code paths.

**Applies to:** controller files, service files, middleware files

---

### PERF-005 — Response payloads must not load entire collections into memory
**Source:** `01-architecture.md#performance-constraints`
**Severity default:** medium

Loading entire DB collections into memory before serializing is a memory hotspot.
Use streaming, pagination, or projection (select only needed fields).

**Applies to:** service files, serializer files

---

### PERF-006 — Cache invalidation must not fetch the full dataset on miss
**Source:** `01-architecture.md#caching-policy`
**Severity default:** medium

Cache-miss handlers must fetch only the specific resource, not the full collection.
Stampede protection (e.g. mutex/lock) is required for hot keys.

**Applies to:** cache service files, repository files with caching layer
