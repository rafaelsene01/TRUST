# Data Checklist

> Source of truth: `grounding/04-data-model.md`
> Maintained by: {{TEAM_NAME}}
> Last reviewed: {{DATE}}

Each rule must have a unique `rule_id` in format `DAT-XXX`, a `source` pointing to
a section in the data model grounding doc, and a clear, testable `title`.

---

### DAT-001 — Migrations must be reversible
**Source:** `04-data-model.md#migration-safety`
**Severity default:** high

Every migration must include a rollback path (`down` / `revert` / `rollback`).
Irreversible migrations must be explicitly documented as such in a companion ADR.

**Applies to:** migration files

---

### DAT-002 — No column drops without a deprecation period
**Source:** `04-data-model.md#schema-evolution`
**Severity default:** critical

Dropping a column removes data permanently. Columns must be marked as
deprecated (via comment + deprecation ADR) for at least one release cycle
before a drop migration is allowed.

**Applies to:** migration files

---

### DAT-003 — NOT NULL columns require a default or backfill in the same migration
**Source:** `04-data-model.md#migration-safety`
**Severity default:** critical

Adding a `NOT NULL` constraint to a column on a table with existing rows will fail
unless a `DEFAULT` is provided or the same migration backfills all existing rows.

**Applies to:** migration files

---

### DAT-004 — Foreign keys must have a corresponding index
**Source:** `04-data-model.md#indexing-policy`
**Severity default:** high

Every foreign key column must have an index to prevent full-table scans on
join operations. The index must be created in the same migration as the FK.

**Applies to:** migration files

---

### DAT-005 — Large table index creation must use CONCURRENTLY or equivalent
**Source:** `04-data-model.md#migration-safety`
**Severity default:** high

Creating an index on a large table locks it for writes. Use `CREATE INDEX CONCURRENTLY`
(Postgres), `ALGORITHM=INPLACE` (MySQL), or equivalent to avoid downtime.

**Applies to:** migration files for tables with production data

---

### DAT-006 — Enum additions must be backward-compatible
**Source:** `04-data-model.md#schema-evolution`
**Severity default:** high

Adding values to an existing enum is safe. Removing or renaming enum values
is a breaking change — all existing rows storing the removed value become invalid.

**Applies to:** migration files, schema files with enum definitions

---

### DAT-007 — Data type changes must be explicitly compatible
**Source:** `04-data-model.md#schema-evolution`
**Severity default:** critical

Changing a column's data type (e.g. `INT` → `BIGINT`, `VARCHAR(50)` → `TEXT`)
may fail silently or truncate data. The migration must validate compatibility
or include a data migration step.

**Applies to:** migration files

---

### DAT-008 — Seeder scripts must be idempotent
**Source:** `04-data-model.md#seeder-policy`
**Severity default:** medium

Seeder scripts must handle re-runs gracefully (upsert, not insert). Running a
seeder twice must produce the same result, not duplicate data.

**Applies to:** seed/fixture files
