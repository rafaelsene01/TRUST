# TRUST — Project Handoff

> **Trustable Reviews via Universal Skills & Tooling**
> *"O review de IA em que dá pra confiar"*
>
> Documento de finalização da fase de design e MVP.
> Data: 2026-05-18

---

## O que foi construído

TRUST é um framework de Pull Request Review com agentes de IA, desenhado para
resolver um problema específico: **reviews de IA que devs ignoram depois de 3
sprints**. A causa raiz é sempre a mesma — prompt genérico, sem contexto do
projeto, falsos positivos, hallucinations. O TRUST ataca cada um desses sintomas
com uma camada arquitetural própria.

O projeto passou por quatro estágios nesta sessão:

1. **Conceituação** — os 7 pilares, os 4 profiles operacionais, a filosofia de
   Definition of Done estrito
2. **Arquitetura** — modelo de 3 repos (framework / setup / produto), sources
   plugáveis, hierarquia de camadas, sistema de HALT
3. **Documentação** — README + 5 docs temáticos + glossário + plano de
   implementação em fases
4. **MVP funcional** — core Python, adapter filesystem, skill security completa,
   8 fases do pipeline, 8/8 testes E2E passando

---

## Estado atual — MVP v0.1.0

### O que está pronto e funcionando

| Componente | Arquivos | Status |
| --- | --- | --- |
| Core — models | `core/models.py` | ✅ Completo |
| Core — config loader | `core/config_loader.py` | ✅ Completo |
| Core — grounding loader | `core/grounding_loader.py` | ✅ Completo |
| Core — halt handler | `core/halt_handler.py` | ✅ Completo |
| Core — run manifest | `core/run_manifest.py` | ✅ Completo |
| Core — orchestrator | `core/orchestrator.py` | ✅ Completo (8 fases) |
| Adapter filesystem | `adapters/filesystem_adapter.py` | ✅ Completo |
| Skill security | `skills/trust-security-review/` | ✅ Estrutural (ver gaps abaixo) |
| Slash commands | `commands/trust-*.md` | ✅ Completo (4 comandos) |
| Templates | `templates/` | ✅ Completo |
| Testes E2E | `tests/e2e/test_mvp.py` | ✅ 8/8 passando |
| Documentação | `docs/` + `README.md` | ✅ Completo |
| Script de install | `install.sh` | ✅ Completo |

### O que ainda não está pronto (pós-MVP)

| Item | Onde está documentado | Prioridade |
| --- | --- | --- |
| 4 scripts Python da skill security | `SKILL_COMPLETION_PLAN.md` — E1 | 🔴 Alta |
| 3 assets ausentes da skill | `SKILL_COMPLETION_PLAN.md` — E2 | 🔴 Alta |
| SECOND_PASS.md + update PROTOCOL.md | `SKILL_COMPLETION_PLAN.md` — E3 | 🔴 Alta |
| 14 testes isolados da skill | `SKILL_COMPLETION_PLAN.md` — E4 | 🟠 Média |
| Exemplos adicionais no SKILL.md | `SKILL_COMPLETION_PLAN.md` — E5 | 🟠 Média |
| 5 agentes restantes | `IMPLEMENTATION_PLAN.md` — v1.0 | 🟠 Média |
| Skill second-pass | `IMPLEMENTATION_PLAN.md` — v1.0 | 🟠 Média |
| Skill meta-review | `IMPLEMENTATION_PLAN.md` — v1.0 | 🟠 Média |
| Adapter Notion + HTTP | `IMPLEMENTATION_PLAN.md` — v1.1 | 🟡 Baixa |
| Rastreabilidade Jira/Spec | `IMPLEMENTATION_PLAN.md` — v1.2 | 🟡 Baixa |
| Profiles Team/Solo/Enterprise | `IMPLEMENTATION_PLAN.md` — v2.0 | 🟡 Baixa |

---

## Estrutura de arquivos entregues

```
trust/
│
├── README.md                          # fonte da verdade — leia primeiro
├── IMPLEMENTATION_PLAN.md             # roadmap completo MVP → v2.1
├── CHANGELOG.md                       # histórico de versões
├── LICENSE                            # MIT
├── install.sh                         # instalação one-liner
├── requirements.txt                   # PyYAML >= 6.0
├── .gitignore
│
├── core/                              # motor do framework (Python)
│   ├── models.py                      # dataclasses compartilhadas
│   ├── config_loader.py               # lê trust.config.yaml
│   ├── grounding_loader.py            # carrega docs via adapters
│   ├── halt_handler.py                # gerencia HALTs e markers
│   ├── run_manifest.py                # ciclo de vida de cada run
│   └── orchestrator.py               # driver das 8 fases
│
├── adapters/                          # sources plugáveis
│   └── filesystem_adapter.py         # lê do disco (MVP); notion/http em v1.1
│
├── skills/
│   └── trust-security-review/         # skill agentskills.io compliant
│       ├── SKILL.md                   # frontmatter + escopo + golden rules
│       ├── SKILL_COMPLETION_PLAN.md   # plano para fechar a skill (próxima etapa)
│       ├── references/
│       │   ├── PROTOCOL.md            # 8 passos de execução do agente
│       │   ├── FINDING_FORMAT.md      # schema canônico de finding
│       │   ├── DOD.md                 # critérios + self-attestation block
│       │   └── GOTCHAS.md             # edge cases e armadilhas
│       ├── scripts/
│       │   └── validate_coverage.py   # valida 100% de cobertura
│       └── assets/
│           ├── finding-template.json  # JSON Schema de finding
│           └── coverage-template.json # JSON Schema de coverage matrix
│
├── commands/                          # slash commands do Claude Code
│   ├── trust-review-pr.md             # /trust review-pr
│   ├── trust-init.md                  # /trust init
│   ├── trust-doctor.md                # /trust doctor
│   └── trust-cleanup.md               # /trust cleanup
│
├── templates/                         # gerados pelo /trust init
│   ├── trust.config.yaml.template     # config do setup repo
│   ├── trust.config.pilot.yaml        # config completo modo Pilot
│   ├── target.yaml.template           # config por repo-alvo
│   ├── checklists/
│   │   └── security.checklist.md      # 12 regras starter de segurança
│   └── grounding/
│       └── 06-security-policy.md      # política de segurança template
│
├── docs/                              # documentação temática
│   ├── 01-conceitos.md                # 7 pilares, profiles, filosofia
│   ├── 02-arquitetura.md              # 3 repos, 8 fases, adapters, layers
│   ├── 03-onboarding.md               # instalação → primeiro review
│   ├── 04-skills-spec.md              # padrão agentskills.io
│   └── 05-glossario.md                # vocabulário do TRUST
│
└── tests/
    ├── e2e/
    │   └── test_mvp.py                # 8 testes E2E (todos passando)
    └── fixtures/
        ├── mock-diff/
        │   └── feat-PAY-123.patch     # diff com bugs intencionais (SQLi, secret)
        └── mock-grounding/
            └── *.md                   # 7 docs de grounding para testes
```

---

## Como subir para o GitHub

```bash
# 1. Descompactar o zip
unzip trust-v0.1.0-mvp.zip
cd trust

# 2. Inicializar o repositório
git init
git add .
git commit -m "feat: TRUST MVP v0.1.0

- 8-phase review pipeline with strict DoD enforcement
- trust-security-review skill (agentskills.io spec compliant)
- Filesystem grounding adapter
- Pilot profile: setup repo decoupled from product repo
- /trust review-pr, init, doctor, cleanup commands
- 8/8 E2E tests passing"

# 3. Conectar ao GitHub
# Crie o repo em github.com (sem README, sem .gitignore — já temos os nossos)
git remote add origin git@github.com:<seu-usuario>/trust.git
git branch -M main
git push -u origin main

# 4. Tag da versão
git tag -a v0.1.0-mvp -m "MVP: vertical slice com agente security"
git push origin v0.1.0-mvp
```

---

## Como continuar o desenvolvimento

### Próxima sessão imediata — fechar a skill security

O arquivo `skills/trust-security-review/SKILL_COMPLETION_PLAN.md` é o guia
completo. Executar os 5 entregáveis nesta ordem:

```
E1 → 4 scripts Python (check_evidence_literal, parse_checklist,
                        validate_dod_attestation, check_rule_source)
E2 → 3 assets (dod-attestation-template, second-pass-template,
                non-finding-reasons.md)
E3 → 2 docs (SECOND_PASS.md, update PROTOCOL.md steps 7-8)
E4 → 14 testes isolados da skill
E5 → 3 exemplos no SKILL.md + verificação cruzada + README da skill
```

Quando todos os 16 checkboxes do DoD global da skill estiverem marcados,
a skill passa de `v1.0.0 (MVP estrutural)` para `v1.1.0 (production-ready)`.

### Sessão seguinte — v1.0 Pilot Ready

Com a skill security production-ready, replicar o padrão para os 5 agentes
restantes e implementar as fases faltantes (Second Pass e Meta-review completo).
Detalhes em `IMPLEMENTATION_PLAN.md — Fase v1.0`.

---

## Decisões de design tomadas (não reverter sem ADR)

Estas decisões foram deliberadas e estão refletidas em todo o codebase. Mudar
qualquer uma requer discussão e um ADR formal.

| Decisão | Racional |
| --- | --- |
| **Modo estrito por padrão** — HALT em qualquer DoD falho | Falha silenciosa é pior que HALT visível. O dev pode investigar um HALT; não pode investigar algo que "passou" silenciosamente. |
| **Repo do produto 100% limpo** (Pilot mode) | Zero resistência política. Outros times não veem arquivos estranhos. Governança no repo correto. |
| **IA nunca aprova nem rejeita** | Pilar 5 irrevogável. Qualquer feature que automatize aprovação viola o contrato do framework. |
| **Precision > Recall** — limiar 0.80 | Um falso positivo custa mais que uma omissão. Cry wolf destrói confiança permanentemente. |
| **evidence_quote literal obrigatório** | Paráfrase é hallucination. O meta-reviewer valida byte a byte. |
| **Grounding first, sempre** | Sem contexto do projeto, a IA usa conhecimento genérico — que contradiz ADRs do time. |
| **Sources plugáveis desde o início** | Não forçar filesystem como única opção trava adoção em empresas com Confluence/Notion. |
| **Python para scripts** | Aderência à spec agentskills.io. Scripts são pequenos, sem dependências pesadas, testáveis. |

---

## Métricas de sucesso do piloto

Quando o time piloto rodar o TRUST em produção, medir:

| Métrica | Meta MVP | Meta v1.0 |
| --- | --- | --- |
| Adoção — % PRs com review TRUST | > 50% | > 80% |
| False positive rate | < 30% | < 20% |
| Hallucinations por 100 findings | < 5 | < 1 |
| HALT rate (DoD falhos) | < 10% | < 5% |
| NPS dos devs (1-10) | ≥ 6 | ≥ 7 |
| Time-to-review (PR 50 arquivos) | < 10 min | < 5 min |

---

*Gerado em 2026-05-18 · TRUST v0.1.0-mvp · MIT License*
