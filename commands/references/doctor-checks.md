# /trust doctor — Checks Reference

All checks performed by `/trust doctor`, with pass/fail criteria and output format.

## 1. Environment

| Check | Pass | Fail |
| --- | --- | --- |
| `TRUST_SETUP_PATH` is set | ✅ | ❌ — shows how to set it |
| `TRUST_SETUP_PATH` exists on disk | ✅ | ❌ — shows `git clone` command |
| `trust.config.yaml` present and valid YAML | ✅ | ❌ — shows the parse error |
| Python 3.11+ available | ✅ | ⚠️  warning |
| `git` available | ✅ | ❌ |

## 2. Grounding sources

For each source declared in `trust.config.yaml`:

| Check | Pass | Fail |
| --- | --- | --- |
| Adapter is supported | ✅ | ❌ |
| Base path resolves to an existing directory | ✅ | ❌ offers to configure |
| Required docs exist in source | ✅ | ❌ lists missing docs |
| No required doc is empty (< 200 bytes) | ✅ | ⚠️  lists stub files |

## 3. Targets

For each `targets/*.yaml`:

| Check | Pass | Fail |
| --- | --- | --- |
| File is valid YAML | ✅ | ❌ |
| `remote_url` field is present | ✅ | ⚠️  warning |
| `repo_path` resolves on this machine | ✅ | ⚠️  prompts to configure |
| Enabled agents have their SKILL.md | ✅ | ❌ |
| Checklist files referenced by agents exist | ✅ | ❌ |

## 4. Skills

For each skill referenced in config:

| Check | Pass | Fail |
| --- | --- | --- |
| SKILL.md exists | ✅ | ❌ — re-install framework |
| SKILL.md has YAML frontmatter | ✅ | ❌ |
| References listed in SKILL.md exist | ✅ | ⚠️  |

## 5. Integrations

Para cada integração em `config.integrations` onde `source != disabled`:

| Check | Pass | Fail |
| --- | --- | --- |
| `source: mcp` → MCP tool disponível na sessão atual | ✅ | ⚠️ aviso: MCP não detectado, considere `source: api` |
| `source: gh-cli` → `gh` instalado no PATH | ✅ | ❌ `gh` CLI não encontrado → instale em https://cli.github.com |
| `source: gh-cli` → `gh auth status` exit 0 | ✅ | ❌ gh não autenticado → `gh auth login` |
| `source: api` → env vars declaradas em `auth` estão presentes | ✅ | ❌ lista as vars faltando com instrução de como setar |
| `source: auto` → pelo menos um caminho (MCP ou env vars) disponível | ✅ | ⚠️ aviso com instrução |
| `source: api`, Jira → `JiraClient.health_check()` retorna ok | ✅ | ❌ mostra erro e próximo passo |
| `source: api`, Notion → `NotionAdapter.health_check()` retorna ok | ✅ | ❌ mostra erro e próximo passo |
| `traceability.enabled: true` → Jira source != disabled | ✅ | ❌ inconsistência: ativar Jira ou desativar traceability |

Integrações com `source: disabled` são silenciosamente ignoradas (sem output).

## Output format

```
🩺 TRUST doctor — health check

Environment
  ✅ TRUST_SETUP_PATH = ~/work/payments-team-trust
  ✅ trust.config.yaml valid
  ✅ Python 3.11 found
  ✅ git found

Grounding sources
  ✅ in-setup (filesystem) — ./grounding/
     7 required docs present (47KB total)
  ⚠️  second-brain (filesystem) — TRUST_SECONDBRAIN_PATH not set
     → To configure: add TRUST_SECONDBRAIN_PATH=<path> to .env.local
     → Or disable: set optional: true in config (already set)

Targets
  ✅ api-payments — repo path found, 6 agents configured
  ⚠️  payments-frontend — repo_path not found on this machine
     ~/work/payments-frontend does not exist
     → Clone it or update repo_path in targets/payments-frontend.yaml

Skills
  ✅ trust-security-review — SKILL.md valid, 4 references present

Integrations
  ✅ jira (mcp) — MCP Atlassian detectado na sessão
  ✅ notion (disabled) — skip
  ⚠️  confluence (auto) — nenhum acesso disponível
     MCP não detectado e CONFLUENCE_TOKEN não está no ambiente
     → Opção 1: configure source: mcp (se tiver MCP Atlassian)
     → Opção 2: export CONFLUENCE_USER=... e CONFLUENCE_TOKEN=... em .env.local
     → Opção 3: set source: disabled para ignorar Confluence
  ✅ github (mcp) — MCP GitHub detectado na sessão
  ✅ github (gh-cli) — autenticado como rafaelsene01
  ❌ github (gh-cli) — gh não autenticado
     → Next action: gh auth login
  ❌ github (gh-cli) — gh CLI não encontrado
     → Next action: instale em https://cli.github.com

─────────────────────────────
Status: 2 warnings, 0 errors

No errors found — you can run /trust review-pr
```

Exit code 1 when errors are found.
