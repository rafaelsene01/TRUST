# /trust init team — Setup Protocol

In team profile, TRUST config lives **inside the product repo** under `.trust/`.
No separate setup repo — grounding and checklists travel with the codebase.

## Step 1 — Welcome

```
╭─ TRUST — Team Mode ──────────────────────────────────────╮
│  Config lives in the product repo under .trust/          │
│  All devs get the same setup automatically via git       │
╰──────────────────────────────────────────────────────────╯
```

## Step 2 — Confirm product repo

```
📁 Product repo path (current dir if empty):
   Detected: ~/work/payments-api
>
```

## Step 3 — Team name

```
🏷️  Team name:
>
```

## Step 4 — Grounding sources

```
📚 Where will grounding documents live?

[1] .trust/grounding/      — committed alongside code (recommended)
[2] External (Notion, Confluence)
[3] Both
>
```

## Step 5 — Generate files

Create inside the product repo:

```
.trust/
├── trust.config.yaml
├── .env.example
├── grounding/
│   ├── _drafts/
│   ├── 01-architecture.md
│   ├── 02-domain-glossary.md
│   ├── 03-api-contracts.md
│   ├── 04-data-model.md
│   ├── 05-conventions.md
│   ├── 06-security-policy.md
│   └── 07-adrs/
├── checklists/
│   ├── security.checklist.md
│   ├── contracts.checklist.md
│   ├── data.checklist.md
│   ├── performance.checklist.md
│   ├── conventions.checklist.md
│   └── tests.checklist.md
└── runs/          ← add to .gitignore
```

Add to repo's `.gitignore`:
```
.trust/runs/
.trust/.env.local
```

## Step 6 — Print next steps

```
✅ Setup created at .trust/

📋 Next steps:
   1. git add .trust/ && git commit -m "chore: add TRUST team config"
   2. Fill grounding stubs in .trust/grounding/
   3. export TRUST_SETUP_PATH=$(pwd)/.trust
   4. /trust doctor
   5. /trust review-pr
```
