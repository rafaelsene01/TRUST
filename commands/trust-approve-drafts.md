---
description: Promove rascunhos de grounding revisados de grounding/_drafts/ para grounding/, tornando-os ativos para os reviews
---

# /trust approve-drafts

Promotes reviewed draft grounding documents from `grounding/_drafts/` to `grounding/`.

Run this after `/trust map codebase` and after you've reviewed and edited the drafts.
A draft must not contain any `TODO` markers to be approved — they signal missing human input.

## Usage

```
/trust approve-drafts [--all] [<filename>...]
```

| Form | What it does |
| --- | --- |
| `/trust approve-drafts --all` | Promotes every draft that has no `TODO` markers |
| `/trust approve-drafts 01-architecture.md` | Promotes only that specific draft |
| `/trust approve-drafts` (no args) | Lists pending drafts and asks which to approve |

---

## Execution steps

**Step 1 — Validate environment**

Check that `TRUST_SETUP_PATH` points to a valid setup repo with a `grounding/_drafts/` directory.
If not found, print instructions to run `/trust map codebase` first.

**Step 2 — Find drafts**

List all `*.md` files in `grounding/_drafts/`. For each:
- Check if it contains any `TODO` marker (case-insensitive line scan)
- Check if the corresponding finalized file already exists in `grounding/`

**Step 3 — Interactive selection (no-args mode)**

Print:
```
📋 Drafts available for promotion:

  ✅ _drafts/01-architecture.md     → grounding/01-architecture.md    [no TODOs]
  ⚠️  _drafts/03-api-contracts.md   → grounding/03-api-contracts.md   [2 TODOs remain]
  ✅ _drafts/05-conventions.md      → grounding/05-conventions.md     [no TODOs]
  🔄 _drafts/06-security-policy.md → grounding/06-security-policy.md [overwrites existing]

Approve which drafts? (space-separated numbers, or 'all' for ✅ only):
```

**Step 4 — Promote selected files**

For each selected draft:
1. If it still has `TODO` markers and `--all` was not used with `--force`, ask to confirm
2. Copy `grounding/_drafts/<file>` → `grounding/<file>`
3. Print confirmation

```
  ✅ Promoted: grounding/01-architecture.md
  ✅ Promoted: grounding/05-conventions.md
  ⏭️  Skipped: grounding/03-api-contracts.md (2 TODOs remain — edit draft and retry)
```

**Step 5 — Print next steps**

```
✅ Grounding updated.

Next:
  /trust doctor    — verify all agents can load their required grounding
  /trust review-pr — run a review with the new grounding
```

---

## Rules for promotion

1. **No TODO markers** — every `TODO:` line must be replaced before the file can be promoted
   without an explicit override. The intent is to prevent lazy approvals.
2. **No empty sections** — a section with only a heading and nothing else is flagged.
3. **Existing files** — if `grounding/<file>` already exists, the command asks for confirmation
   before overwriting.
4. **Drafts are preserved** — the original draft in `_drafts/` is kept after promotion.
   Delete it manually if you want to clean up.

---

## Undoing an approval

There is no automatic rollback. If you approved a bad draft, edit `grounding/<file>` directly
or restore from git:

```bash
git checkout HEAD -- grounding/01-architecture.md
```
