# PROTOCOL — trust-data-review

> Detailed execution protocol. Load this file before touching the diff.

---

## Step 0 — Verify environment

Before anything else, confirm:

- [ ] `TRUST_SETUP_PATH` env var is set and points to a valid setup repo
- [ ] `trust.config.yaml` exists in the setup root and is readable
- [ ] The current target's `target.yaml` has been resolved by the orchestrator
- [ ] The diff is available in the run directory (`<run-dir>/diff.patch`)

If any check fails, **halt** and return a structured error.

---

## Step 1 — Load grounding

Read the following files from the setup repo's `grounding/`:

- `04-data-model.md` — **your primary source of truth** (schema rules, migration safety, data integrity)
- `01-architecture.md` — to understand data ownership and service boundaries
- `07-adrs/` — ADRs that may document intentional schema exceptions (e.g. legacy columns kept for compatibility)

Index sections by anchor. You will reference these as `rule_source` in findings.

If any required doc is missing → **halt**.

---

## Step 2 — Load checklist

Read `checklists/data.checklist.md` from the setup repo. Parse it into a structured list.

If any rule lacks required fields (`rule_id`, `title`, `source` with `#anchor`) → **halt**.

---

## Step 3 — Inventory diff files in domain

Files in the data domain: migration files, schema files, model/entity definitions.

```
file_patterns: ["**/migrations/**", "**/migrate/**", "**/alembic/versions/**",
                "**/*migration*", "**/*schema*", "**/*.sql",
                "**/models/**", "**/entities/**", "prisma/schema.prisma",
                "db/schema.rb"]
```

For each file, determine domain membership. Record counts.

---

## Step 4 — Build the coverage matrix

For every `(rule × file)` pair, produce a verdict.

**Key assessment per rule type:**

- **Reversibility rules** (e.g. DAT-001): does the migration have a `down` or equivalent rollback? Is the rollback non-destructive?
- **NOT NULL rules** (e.g. DAT-003): is a default provided? Is there a backfill? Can existing rows satisfy the constraint?
- **Index rules** (e.g. DAT-004): is an index created when a foreign key is added? Is the index creation online-safe (CONCURRENTLY)?
- **Type change rules** (e.g. DAT-005): is the type change backward-compatible? Will existing data fit?

---

## Step 5 — Generate findings from violations

For every `violation` verdict, produce a finding using `references/FINDING_FORMAT.md`.

Critical reminders:
1. `evidence_quote` from the migration file, literal
2. For multi-line violations (e.g. a full migration `up` block), quote only the relevant statement, not the entire file
3. Confidence calibration: if you can't tell whether a migration is reversible without running it, lower confidence accordingly

---

## Step 6 — Validate findings before emitting

Self-check each finding for required fields, literal quote, confidence ≥ 0.80.

---

## Step 7 — Run all validation scripts

```bash
python scripts/validate_coverage.py <run-dir>/agents/data.coverage.json
```

Exit 0 to proceed.

---

## Step 8 — Self-attest Definition of Done

Read `references/DOD.md`, fill attestation block, write to `<run-dir>/agents/data.dod.json`.
