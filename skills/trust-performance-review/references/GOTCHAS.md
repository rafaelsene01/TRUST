# GOTCHAS — trust-performance-review

> Edge cases specific to performance review. Load when you encounter ambiguous cases.

---

## N+1 detection

### Gotcha: the loop might not execute in practice
A for-loop with a query inside is an N+1 if it runs on a large dataset. But if the
loop is over a known-small set (e.g. a max-3-item configuration list), the performance
impact is negligible. Lower confidence when the collection size is clearly bounded and small.

### Gotcha: DataLoader / batching intermediaries
GraphQL resolvers often use DataLoader to batch queries automatically. A query inside
a resolver `resolve()` method is NOT necessarily an N+1 — DataLoader batches calls within
the same tick. Confirm whether the project uses DataLoader before flagging resolver queries.

### Gotcha: streaming vs loading into memory
Some patterns that look like "load everything" are actually streaming.
`find().stream()`, `cursor()`, generators — these don't load the full result set.
Only flag PERF-005 if the code actually materializes the full collection.

---

## Timeouts

### Gotcha: framework-level default timeouts
Some HTTP frameworks have default timeouts configured globally (e.g. NestJS `HttpModule`
with a global `timeout` interceptor). If the project has this, individual call sites
may not need explicit timeouts. Check `01-architecture.md` or `05-conventions.md`
for this configuration before flagging PERF-003.

### Gotcha: internal service calls vs external calls
Internal calls to services in the same private network often have different timeout
requirements. The checklist rule may only apply to external (third-party) calls.
Read the rule's `applies_to` field carefully.

---

## Index assessment

### Gotcha: the performance agent is NOT the data agent
Do not flag missing indexes unless the checklist has a specific performance rule
about it (e.g. "queries on unindexed columns"). The data agent (trust-data-review)
handles indexing rules. If you see an N+1 that a new index would help, you can
mention the missing index in the `suggestion`, but do not file a separate finding
for it — that's out of your domain.

---

## Common false positives

### Gotcha: test environment code
Performance rules often don't apply in test utilities, fixtures, or seeder scripts
that run once during setup. Mark as N/A with reason "test/seeder code — not a
production hot path".

### Gotcha: admin-only paths
Admin endpoints that serve 10 users total don't need the same perf standards as
user-facing endpoints. Check if the file is in an admin route. If the checklist
is silent on admin exceptions, apply the rules — but note the lower risk in
`false_positive_risk: medium`.
