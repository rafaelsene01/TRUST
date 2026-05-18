# Arquitetura — TRUST

> **Pergunta que este doc responde:** como o TRUST se organiza em arquivos, repos e fluxo de execução.

---

## 1. A arquitetura de 3 repos (Pilot mode)

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│ 1. Framework TRUST  │    │ 2. Setup do Time     │    │ 3. Repo do Produto  │
│   o motor           │ ─→ │   config + regras    │ ─→ │   código do produto │
│   distribuído       │    │   versionado pelo    │    │   100% LIMPO        │
│   uma instalação    │    │   time piloto        │    │   sem TRUST dentro  │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
```

### Repo 1 — Framework TRUST (este repo)

O motor. **Distribuído como plugin do Claude Code.** Cada dev instala uma vez.

```
trust/
├── README.md                       # você está aqui
├── IMPLEMENTATION_PLAN.md
├── LICENSE
├── install.sh                      # instalação one-liner
├── .claude-plugin/                 # manifesto do plugin Claude Code
│   └── plugin.json
├── docs/
│   ├── 01-conceitos.md
│   ├── 02-arquitetura.md
│   └── ...
├── skills/                         # skills aderentes à spec agentskills.io
│   ├── trust-security-review/
│   │   ├── SKILL.md                # com YAML frontmatter
│   │   ├── references/
│   │   ├── scripts/
│   │   └── assets/
│   ├── trust-contracts-review/
│   ├── trust-data-review/
│   ├── trust-performance-review/
│   ├── trust-conventions-review/
│   ├── trust-tests-review/
│   ├── trust-second-pass/
│   ├── trust-precision-gate/
│   └── trust-meta-review/
├── commands/                       # slash commands do Claude Code
│   ├── trust-init.md
│   ├── trust-map.md
│   ├── trust-doctor.md
│   ├── trust-review-pr.md
│   ├── trust-approve-drafts.md
│   └── trust-cleanup.md
├── adapters/                       # sources plugáveis
│   ├── filesystem_adapter.py
│   ├── notion_adapter.py
│   └── http_adapter.py
├── core/                           # lógica do orquestrador
│   ├── orchestrator.py
│   ├── grounding_loader.py
│   ├── target_resolver.py
│   ├── run_manifest.py
│   └── halt_handler.py
└── templates/                      # templates para /trust init
    ├── trust.config.yaml.template
    ├── target.yaml.template
    └── grounding/
```

### Repo 2 — Setup do Time

Repositório próprio do time piloto, **separado do produto**. Aqui moram as regras.

```
payments-team-trust/
├── README.md                       # como o time usa TRUST
├── trust.config.yaml               # configuração principal
├── grounding/                      # os 7+ docs do projeto
│   ├── 01-architecture.md
│   ├── 02-domain-glossary.md
│   ├── 03-api-contracts.md
│   ├── 04-data-model.md
│   ├── 05-conventions.md
│   ├── 06-security-policy.md
│   └── 07-adrs/
│       ├── ADR-001-event-sourcing.md
│       └── ADR-002-postgres-uuid.md
├── checklists/                     # regras numeradas por domínio
│   ├── security.checklist.md
│   ├── contracts.checklist.md
│   ├── data.checklist.md
│   ├── performance.checklist.md
│   ├── conventions.checklist.md
│   └── tests.checklist.md
├── skills/                         # SKILL.md customizadas do time (opcional)
│   └── ...
├── targets/                        # um YAML por repo-alvo
│   ├── api-payments.yaml
│   └── payments-frontend.yaml
├── runs/                           # histórico configurável
├── .env.example                    # template de env vars
├── .env.local                      # gitignored — paths absolutos do dev
└── .gitignore
```

### Repo 3 — Repo do Produto (intocado)

**Nenhum arquivo do TRUST aqui.** O repo do produto não sabe que o TRUST existe.

```
api-payments/
├── src/
├── tests/
├── package.json
└── ...                             # NADA do TRUST
```

A ligação entre os 3 é uma única env var no shell do dev:

```bash
export TRUST_SETUP_PATH=~/work/payments-team-trust
```

---

## 2. As 8 fases de execução

Quando o dev roda `/trust review-pr feat/X`, o framework executa 8 fases sequenciais. Cada fase **só inicia se a anterior atingiu seu DoD**.

### Fase 0 — Trigger

**O que faz:** captura o contexto de execução.

- Lê `trust.config.yaml` do setup
- Resolve qual target.yaml se aplica ao cwd (via `git remote`)
- Captura o diff (`git diff main...feat/X`)
- Gera `run-id` único (timestamp + branch hash)
- Inicializa `.review/runs/<run-id>/run-manifest.json`

**DoD da Fase 0:**
- ✓ `trust.config.yaml` carregado e validado
- ✓ target.yaml resolvido (ou usuário foi solicitado)
- ✓ diff capturado e indexado por hunk
- ✓ run-id gerado

### Fase 1 — Grounding obrigatório

**O que faz:** carrega todos os docs listados em `grounding.required`.

- Para cada source declarada, chama o adapter correspondente
- Lê os docs, calcula sha256 (exceto sources volatile)
- Indexa as seções para os agentes consumirem
- Grava `grounding.manifest.json` com todos os hashes

**DoD da Fase 1:**
- ✓ 100% dos docs `required` existem
- ✓ Nenhum doc obrigatório com menos de 5KB (sanity check)
- ✓ sha256 registrado para cada doc não-volatile
- ✓ Nenhuma source obrigatória inacessível

**Se falhar:** HALT. O dev resolve as sources ausentes/inválidas via `/trust doctor`.

### Fase 2 — Agentes especialistas em paralelo

**O que faz:** dispara os 6 agentes que se aplicam ao target.

Cada agente:
1. Carrega APENAS seu próprio `SKILL.md` + checklist + grounding
2. Constrói a matriz **regra × arquivo** (cada combinação tem veredito)
3. Produz `<dominio>.findings.json` e `<dominio>.coverage.json`

**DoD da Fase 2 (por agente):**
- ✓ 100% dos arquivos do domínio avaliados
- ✓ 100% das regras do checklist com veredito (compliant | violation | not_applicable)
- ✓ Toda regra `not_applicable` tem justificativa
- ✓ Todo finding tem `rule_id`, `rule_source`, `evidence_quote` literal e `confidence`

### Fase 3 — Second Pass

**O que faz:** cada agente re-lê o diff e justifica o que NÃO reportou.

- Lista todos os hunks do diff
- Marca cada hunk: virou finding OU foi clareado explicitamente
- Hunks "unaccounted" disparam HALT

**DoD da Fase 3:**
- ✓ `hunks_unaccounted == 0`
- ✓ Cada non-finding tem `reason_not_reported`

### Fase 4 — Precision Gate

**O que faz:** filtra findings por confiança.

- Findings com `confidence ≥ 0.80` → passam para o REVIEW principal
- Findings com `confidence < 0.80` → vão para anexo `silenced`
- Nenhum finding é **excluído** — apenas separado

**DoD da Fase 4:**
- ✓ Todo finding está em `passed` OU `silenced` (nenhum perdido)
- ✓ Contadores antes/depois batem

### Fase 5 — Meta-Review (anti-hallucination)

**O que faz:** valida cada finding contra a realidade do diff.

Para cada finding, executa 4 checks:
1. `file_exists_in_diff` — o arquivo citado existe?
2. `line_exists_in_diff` — a linha citada existe?
3. `evidence_quote_is_literal` — o quote bate caractere-a-caractere?
4. `rule_source_resolves` — a seção do grounding citada existe?

Falhou qualquer um → finding vai para anexo `hallucinations_caught` com motivo.

**DoD da Fase 5:**
- ✓ 4 validações executadas em cada finding
- ✓ Cada hallucination tem razão registrada

### Fase 6 — Rastreabilidade (opcional)

**O que faz:** se Jira/spec configurado, cruza findings contra requisitos.

- Se `traceability.enabled: false` → pula com flag explícita
- Se `true` → cada finding ganha `traced_to` (ticket Jira ou `.spec.md`)

**DoD da Fase 6:**
- ✓ Se enabled: todo finding tem `traced_to` ou `untraceable_reason`
- ✓ Se disabled: skip está registrado no manifesto

### Fase 7 — Output ao dev

**O que faz:** gera o `REVIEW.md` final.

- Agrupa findings por severidade
- Inclui anexos: silenced, hallucinations
- Contadores cruzados entre fases para garantir integridade
- Opcionalmente posta no PR via `gh`/`glab` (configurável por target)
- Atualiza `run-manifest.json` para `overall_status: passed`

**DoD da Fase 7:**
- ✓ Contadores batem entre todas as fases
- ✓ `run-manifest.json` tem todas as fases marcadas como done
- ✓ A IA não decidiu aprovação/rejeição em momento algum

---

## 3. Sources plugáveis (sistema de adapters)

Grounding pode vir de **qualquer fonte** desde que tenha um adapter. O contrato é simples:

```python
# adapters/base.py (pseudocódigo)

class GroundingAdapter(ABC):
    @abstractmethod
    def list(self, source_config: dict) -> list[DocMetadata]: ...

    @abstractmethod
    def read(self, source_config: dict, path: str) -> DocContent: ...

    @abstractmethod
    def exists(self, source_config: dict, path: str) -> bool: ...

    @abstractmethod
    def health_check(self, source_config: dict) -> HealthStatus: ...
```

Adapters disponíveis:

| Adapter | Quando usar | Disponível desde |
| --- | --- | --- |
| `filesystem` | Docs em disco — in-repo, second brain, pasta sincronizada | MVP |
| `notion` | Páginas e databases do Notion via API | v1.1 |
| `http` | Confluence, GitLab Wiki, qualquer endpoint autenticado | v1.1 |

**Sources externas (notion/http) têm cache automático** em `.trust-cache/` no setup repo.
O TTL padrão é 60 minutos — configurável com `cache_ttl_minutes` por source.

```yaml
grounding:
  sources:
    - id: "confluence"
      adapter: "http"
      base_url: "https://wiki.empresa.com/api/v2"
      auth:
        type: "bearer"
        token_env: "CONFLUENCE_TOKEN"
      volatile: true
      cache_ttl_minutes: 120

    - id: "notion-arch"
      adapter: "notion"
      auth:
        token_env: "NOTION_TOKEN"
      volatile: true
      cache_ttl_minutes: 60
```

Sources marcadas como **`volatile: true`** (hash muda frequentemente, como Notion) nunca disparam
HALT em caso de mudança de conteúdo entre runs — apenas emitem um aviso informativo.

---

## 4. Hierarquia de camadas (Enterprise mode)

Quando o profile é `enterprise`, o grounding ganha camadas com prioridade:

```yaml
grounding:
  layers:
    - id: "corp"        # priority 1 — mais base
      priority: 1
      sources: ["corp-confluence"]
      override_policy: "warn"

    - id: "team"        # priority 2 — sobrescreve corp se justificar
      priority: 2
      sources: ["in-repo"]
      override_policy: "allow"

    - id: "personal"    # priority 3 — mais específico
      priority: 3
      sources: ["second-brain"]
      override_policy: "warn"
      volatile: true
```

Cada finding carrega `provenance` indicando de qual layer veio e se houve override:

```json
"provenance": {
  "layer": "team",
  "overrides": "corp:SEC-007",
  "override_reason": "Time exige bcrypt rounds >= 12, corp pede >= 10"
}
```

---

## 5. Run lifecycle e artefatos

Cada execução do `/trust review-pr` cria uma pasta:

```
.review/runs/2026-05-17-1430-feat-PAY-123/
├── run-manifest.json              # sumário das fases e status
├── grounding.manifest.json        # docs + hashes da Fase 1
├── agents/
│   ├── security.findings.json
│   ├── security.coverage.json
│   ├── security.second-pass.json
│   └── ...
├── gate.report.json               # Fase 4
├── meta-review.json               # Fase 5
├── traceability.json              # Fase 6 (ou skip flag)
└── REVIEW.md                      # output final da Fase 7
```

**Política de retenção** (configurável):

| Política | Sucesso | Halt |
| --- | --- | --- |
| `all_versioned` | Mantém tudo | Mantém tudo |
| `audit_failures_only` ★ | Apaga JSONs, mantém REVIEW.md | Mantém tudo |
| `gitignored` | Tudo local de cada dev | Tudo local |
| `ephemeral` | Apaga tudo | Mantém tudo |

A política padrão recomendada é `audit_failures_only` — só halts ficam versionados.

---

---

## 6. UX e observabilidade (v1.1)

### Progress reporter

O `core/progress_reporter.py` mostra uma barra de progresso por fase durante a execução.
Fases mais rápidas que 1 segundo não mostram barra (evita flicker em runs rápidas).

```
  ✅ Trigger          (0.3s)
  ✅ Grounding        [████████████████████████] 100%  (1.2s)
  ✅ Agents           [████████████████░░░░░░░░]  67%  4m18s  Loading security...
```

Em ambientes sem suporte ANSI (CI, terminais dumb), o reporter cai graciosamente para
texto simples.

### Mensagens de erro acionáveis

Todo erro do framework inclui uma linha `Next action:` explícita:

```
✗ Bearer token env var 'CONFLUENCE_TOKEN' is not set or empty.
  → Next action: export CONFLUENCE_TOKEN=<your-token> in your shell,
    or add it to .env.local
```

Isso aplica a: adapters externos, configuração inválida, HALT de DoD, erros de rede.

### Histórico de runs (`/trust runs`)

```
/trust runs list             # últimas 10 runs
/trust runs show <run-id>    # inspecionar uma run específica
/trust runs clean --older-than 30  # limpar runs antigas
```

**Próximo:** [docs/03-onboarding.md](03-onboarding.md) — instalação, init, doctor, primeiro review na prática.
