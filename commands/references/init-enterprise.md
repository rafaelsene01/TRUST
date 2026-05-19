# /trust init enterprise — Setup Protocol

In enterprise profile, TRUST uses a **hierarchical layer structure**:
`corp/` → `team/` → `personal/` — higher-priority layers override lower ones.
Override policy is auditable: each override requires a `reason`.

## Step 1 — Welcome

```
╭─ TRUST — Enterprise Mode ────────────────────────────────╮
│  Three-layer hierarchy: corp → team → personal           │
│  Every override is auditable                             │
╰──────────────────────────────────────────────────────────╯
```

## Step 2 — Enterprise root

```
📁 Where should the enterprise setup live?
   Suggested: ~/work/<company>-trust
>
```

## Step 3 — Layer configuration

```
🏢 Corp layer — organization-wide rules (read-only for teams)
   Path (or press Enter to create empty):
>

👥 Team layer — your team's rules (inherits + overrides corp)
   Team name:
>

👤 Personal layer — your personal overrides (optional)
   Include personal layer? [y/n]:
>
```

## Step 4 — Override policy

```
🔒 Override policy for team → corp:
[1] allow          — teams can override any corp rule silently
[2] require_reason — overrides must include a reason (recommended)
[3] deny           — no overrides allowed
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

Se [2] em qualquer integração, pedir credenciais e salvar em `personal/.env.local` (nunca commitado).

Se Jira configurado (source != disabled): setar `traceability.enabled: true` automaticamente.

Nota enterprise: integrações com `source: mcp` ou `source: api` podem ser declaradas na camada `corp/` como padrão, com teams podendo sobrescrever via `overrides.yaml` (com `reason` obrigatório se `require_reason`).

## Step 6 — Generate files

```
<enterprise_root>/
├── trust.config.yaml       ← profile: enterprise, layers block
├── corp/
│   ├── grounding/
│   ├── checklists/
│   └── overrides.yaml      ← override policy
├── team/
│   ├── grounding/
│   ├── checklists/
│   └── overrides.yaml      ← team overrides with reasons
├── personal/               ← if enabled
│   └── overrides.yaml
└── runs/
```

## Step 7 — Migration from pilot

If migrating from pilot profile, run:
```
python scripts/migrate_pilot_to_enterprise.py \
  --source ~/work/old-team-trust \
  --output <enterprise_root> \
  --dry-run
```

Then review the output and run without `--dry-run`.

## Step 8 — Print next steps

```
✅ Enterprise setup created at <enterprise_root>

📋 Next steps:
   1. Fill corp/grounding/ with org-wide standards
   2. Fill team/grounding/ with team-specific context
   3. Review override policy in corp/overrides.yaml
   4. export TRUST_SETUP_PATH=<enterprise_root>
   5. /trust doctor
```
