# /trust init solo — Setup Protocol

In solo profile, TRUST uses your **second brain as primary grounding source**.
Config lives in `~/.trust-solo/` — no shared repo, no team coordination needed.

## Step 1 — Welcome

```
╭─ TRUST — Solo Mode ──────────────────────────────────────╮
│  Your second brain is your grounding source              │
│  Reviews stay local — zero shared infrastructure needed  │
╰──────────────────────────────────────────────────────────╯
```

## Step 2 — Second brain location

```
🧠 Where is your second brain / knowledge base?
   Detected: ~/Documents/Obsidian
>
```

Save as `TRUST_SECONDBRAIN_PATH`.

## Step 3 — Solo config location

```
📁 Where should I create your solo config?
   Suggested: ~/.trust-solo
>
```

## Step 4 — Product repos

```
🎯 Which repos do you review most?
   (TRUST will detect the active repo at runtime — this is just for presets)

Repo 1 path (optional, press Enter to skip):
>
```

## Step 5 — Integrações externas

```
🔌 Quais ferramentas externas você usa? (selecione todas que se aplicam)

  [ ] 1. Jira
  [ ] 2. Notion
  [ ] 3. Confluence
  [ ] 4. GitHub

> (ex: 1 3 para Jira e Confluence, ou Enter para nenhuma)
```

Para cada ferramenta marcada, perguntar como acessa:

```
Jira — como você acessa?
  [1] MCP já configurado no Claude Code (sem token necessário)
  [2] API token (JIRA_USER + JIRA_TOKEN)
>

Notion — como você acessa?
  [1] MCP já configurado no Claude Code
  [2] API token (NOTION_TOKEN)
>

Confluence — como você acessa?
  [1] MCP Atlassian já configurado (mesmo MCP do Jira)
  [2] API token (CONFLUENCE_USER + CONFLUENCE_TOKEN)
>

GitHub — como você acessa?
  [1] MCP GitHub já configurado
  [2] gh CLI (já instalado)
>
```

Ferramentas não marcadas → `source: disabled` automaticamente, sem perguntas.

Se [2] em qualquer integração, pedir credenciais e salvar em `~/.trust-solo/.env.local` (não compartilhado).

Se Jira configurado (source != disabled): setar `traceability.enabled: true` automaticamente.

## Step 6 — Generate files

Create at `~/.trust-solo/`:

```
~/.trust-solo/
├── trust.config.yaml       ← profile: solo, secondbrain source
├── .env.local              ← TRUST_SECONDBRAIN_PATH=<path>
├── checklists/             ← personal rules (not shared)
│   └── security.checklist.md
└── runs/
```

`trust.config.yaml` uses `volatile: true` on second-brain sources so
content changes never block a review.

## Step 7 — Print next steps

```
✅ Solo config created at ~/.trust-solo/

📋 Next steps:
   1. export TRUST_SETUP_PATH=~/.trust-solo
   2. Add to your shell rc: export TRUST_SETUP_PATH=~/.trust-solo
   3. /trust doctor
   4. /trust review-pr
```
