# GOTCHAS — trust-data-review

> Edge cases specific to data/migration review. Load when you encounter ambiguous cases.

---

## Migration reversibility

### Gotcha: destructive operations with backups
Some migrations are intentionally irreversible (e.g. dropping PII after a retention
period) but are accompanied by a backup step in the same migration.
These may be compliant with the project's policy — check `04-data-model.md#migration-safety`
to see if backup-then-drop is an allowed pattern.

### Gotcha: `squash` or `consolidation` migrations
Projects sometimes squash many migrations into one initial state migration.
These are inherently irreversible but are a one-time action on a fresh DB.
Check if the migration file is named or commented as a squash — if so,
DAT-001 (reversibility) is N/A.

---

## NOT NULL and defaults

### Gotcha: NOT NULL with no rows in production
If the migration is for a brand new table (created in the same PR or migration batch),
adding NOT NULL without a default is safe — there are no existing rows.
Look for a `create_table` in the same migration or a prior migration in the same PR.
Lower confidence if you can confirm this.

### Gotcha: two-phase NOT NULL migrations
Some teams add NOT NULL in two steps: first add the column as nullable, backfill,
then add the constraint. If the PR only shows the first step, DAT-003 may be N/A
if the second step is documented as a follow-up.

---

## Indexes

### Gotcha: ORM-managed indexes
Prisma, ActiveRecord, and some other ORMs create indexes automatically for
foreign keys. If the ORM is configured to do this, DAT-004 is automatically
satisfied by framework convention — mark as N/A with reason "ORM handles FK indexes automatically".

### Gotcha: composite foreign keys
Some FK constraints span multiple columns. Confirm the index covers the full
composite key, not just one column.

---

## Enum changes

### Gotcha: database-level vs application-level enums
Some projects define enums in the DB (Postgres `CREATE TYPE`), others in the
application layer only. DB-level enum changes require specific migration syntax
and are harder to reverse. Application-level enum changes are safer. Know which
applies before flagging.

---

## Common false positives

### Gotcha: test database migrations
Migrations in `test/` or `spec/` directories are for test environments only.
They often do not need the same safety constraints as production migrations.
Check the file path — if it's clearly a test fixture, lower severity.
