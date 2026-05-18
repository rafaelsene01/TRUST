# /trust init pilot — Setup Protocol

## Step 1 — Welcome

```
╭─ TRUST — Pilot Mode ─────────────────────────────────────╮
│  Trustable Reviews via Universal Skills & Tooling        │
│  "O review de IA em que dá pra confiar"                  │
╰──────────────────────────────────────────────────────────╯

Setting up a TRUST pilot — your team's review config will live
SEPARATE from the product repo. Zero footprint on your codebase.
```

## Step 2 — Setup repo location

```
📁 Where should I create your team's setup repo?
   (suggested: ~/work/<team-name>-trust)
>
```

Validate: parent directory must be writable. If path already exists, ask to confirm overwrite.

## Step 3 — Team name

```
🏷️  Team name (used in README and config):
>
```

## Step 4 — Product repos (targets)

```
🎯 Which product repos will this setup review?
   (you can add more later with /trust target add <path>)

Repo 1 path or URL:
>
```

For each repo entered:
- Try to detect stack from `package.json`, `go.mod`, `pom.xml`, `pyproject.toml`, etc.
- Try to get git remote URL
- Create `targets/<repo-slug>.yaml`
- Ask "Add another? [y/n]"

## Step 5 — Grounding sources

```
📚 Where will your grounding documents live?

[1] In the setup repo itself (./grounding/) — recommended
[2] Your second brain (Obsidian, local Notion export)
[3] Both
>
```

If [2] or [3], ask for path:
```
🧠 Path to your second brain:
   Detected: ~/Documents/Obsidian
>
```

Save as `TRUST_SECONDBRAIN_PATH` in `.env.local` (gitignored).

## Step 6 — SpecForge detection

If `.specforge/` exists in any target repo:
```
🧩 SpecForge detected in <repo-name>.
   Import PROJECT.md and architecture/ as read-only grounding?
   (TRUST will only READ these files, never modify them)
   [y/n]
>
```

## Step 7 — Generate files

Create the following structure:

```
<setup_path>/
├── README.md
├── trust.config.yaml
├── .env.example
├── .env.local              (gitignored — absolute paths)
├── .gitignore
├── grounding/
│   ├── _drafts/
│   ├── 01-architecture.md
│   ├── 02-domain-glossary.md
│   ├── 03-api-contracts.md
│   ├── 04-data-model.md
│   ├── 05-conventions.md
│   ├── 06-security-policy.md
│   └── 07-adrs/
│       └── .gitkeep
├── checklists/
│   ├── security.checklist.md
│   ├── contracts.checklist.md
│   ├── data.checklist.md
│   ├── performance.checklist.md
│   ├── conventions.checklist.md
│   └── tests.checklist.md
├── skills/
├── targets/
│   └── <repo-slug>.yaml
└── runs/
    └── .gitkeep
```

## Step 8 — Print next steps

```
✅ Setup created at <setup_path>

📋 Next steps:
   1. git init && git remote add origin <your-team-trust-repo-url>
   2. Review grounding stubs in grounding/ — fill with your project's real content
   3. /trust map codebase    — auto-generate grounding drafts from your code
   4. /trust doctor          — verify everything is connected
   5. /trust review-pr       — run your first review
```
