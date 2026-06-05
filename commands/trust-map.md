---
description: Escaneia o repo do produto e gera automaticamente rascunhos de documentos de grounding em grounding/_drafts/ para revisão humana
---

# /trust map codebase

Scans the product repo and auto-generates grounding document drafts in `grounding/_drafts/`.

Drafts are **read-only inputs** — you review them, edit what's wrong, then promote with
`/trust approve-drafts`. TRUST never overwrites finalized grounding documents automatically.

## Usage

```
/trust map codebase [--target <repo-slug>] [--force]
```

| Flag | Default | Description |
| --- | --- | --- |
| `--target` | First target in `trust.config.yaml` | Which product repo to scan |
| `--force` | false | Overwrite existing drafts (without this, existing drafts are skipped) |

---

## What it does

Calls `core/codebase_mapper.py` against the product repo and writes one draft per
grounding slot that doesn't already have a finalized document.

Grounding slots and what the mapper extracts:

| Draft file | Extracted from |
| --- | --- |
| `_drafts/01-architecture.md` | Directory tree, main entry points, `README.md` summary |
| `_drafts/03-api-contracts.md` | Route definitions (`router.*`, `app.*`, controllers, decorators) |
| `_drafts/04-data-model.md` | Migration files, schema files (`prisma/schema.prisma`, `*.sql`, ORM models) |
| `_drafts/05-conventions.md` | `.eslintrc*`, `.prettierrc*`, `pyproject.toml`, existing style comments |
| `_drafts/06-security-policy.md` | Auth middleware, CORS config, env var patterns, secret manager calls |

Slots already finalized (file exists in `grounding/` without `_drafts/` prefix) are
**skipped unless `--force` is passed**.

---

## Execution steps

**Step 1 — Validate environment**

Check that `TRUST_SETUP_PATH` points to a valid setup repo.
Check that the target product repo path exists.

If either fails, print a helpful error and exit.

**Step 2 — Run mapper**

```
python core/codebase_mapper.py <product-repo-path> <setup-grounding-path> [--force]
```

The mapper scans the product repo and writes draft files to `<setup-grounding-path>/_drafts/`.

**Step 3 — Print summary**

```
╭─ TRUST map results ──────────────────────────────────────╮
│  Scanned: /path/to/product-repo                          │
│                                                          │
│  Drafts written:                                         │
│    ✅ _drafts/01-architecture.md    (new)                │
│    ✅ _drafts/03-api-contracts.md   (new)                │
│    ⏭️  _drafts/04-data-model.md     (skipped — finalized)│
│    ✅ _drafts/05-conventions.md     (new)                │
│    ✅ _drafts/06-security-policy.md (new)                │
│                                                          │
│  Next: review drafts, then /trust approve-drafts         │
╰──────────────────────────────────────────────────────────╯
```

**Step 4 — Open drafts in editor (optional)**

If Claude Code is running interactively, offer:
```
📂 Open _drafts/ for review? [y/n]
```

---

## Important notes

- Drafts are **starting points**, not final documents. The mapper is heuristic —
  it does not understand your project's intent, only its structure.
- Always review and edit drafts before approving. Especially `06-security-policy.md`
  requires human judgment to fill in the "why" behind each rule.
- If a draft is wrong, edit it in place — `approve-drafts` will pick up your edited version.
- Re-running without `--force` is safe and idempotent for existing drafts.
