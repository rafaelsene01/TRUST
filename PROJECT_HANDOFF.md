# TRUST — Project Handoff

> **Trustable Reviews via Universal Skills & Tooling**
> *"O review de IA em que dá pra confiar"*
>
> Documento de estado do projeto.
> Versão: v2.1.0 · Data: 2026-05-18

---

## O que foi construído

TRUST é um framework de Pull Request Review com agentes de IA, desenhado para
resolver um problema específico: **reviews de IA que devs ignoram depois de 3
sprints**. A causa raiz é sempre a mesma — prompt genérico, sem contexto do
projeto, falsos positivos, hallucinations. O TRUST ataca cada um desses sintomas
com uma camada arquitetural própria.

O projeto foi desenvolvido em 6 fases incrementais, cada uma com DoD verificável:

| Fase | Versão | O que entregou |
| --- | --- | --- |
| MVP | v0.1.0-mvp | Pipeline end-to-end com agente security |
| Skill completa | v0.1.1 | trust-security-review production-ready |
| Pilot Ready | v1.0.0 | 6 agentes + Second Pass + Meta-Review |
| Sources & UX | v1.1.0 | Notion/HTTP adapters, cache, progress bar |
| Rastreabilidade | v1.2.0 | Jira + spec files, Phase 6 operacional |
| Multi-Profile | v2.0.0 | 4 profiles: pilot, team, solo, enterprise |
| Learning Loop | v2.1.0 | Histórico de findings + calibração automática |

---

## Estado atual — v2.1.0

### O que está pronto e funcionando

| Componente | Arquivos | Status |
| --- | --- | --- |
| Core — 17 módulos | `core/` | ✅ Completo · mypy clean |
| Adapters | `adapters/` (filesystem, notion, http) | ✅ Completo |
| Skills specialist | `skills/trust-{security,contracts,data,performance,conventions,tests}-review/` | ✅ 6 skills production-ready |
| Skills pipeline | `skills/trust-{second-pass,meta-review}/` | ✅ Protocol-driven |
| Slash commands | `commands/trust-*.md` (10 comandos) | ✅ Completo |
| Templates | `templates/` (4 profiles, 6 checklists) | ✅ Completo |
| Testes E2E | `tests/e2e/` (7 suites) | ✅ 182/182 passando · 1.5s |
| Testes unitários skill | `tests/skills/test_security_skill.py` | ✅ 14/14 passando |
| Documentação | `docs/` (5 docs temáticos + glossário) | ✅ Completo |
| Script de install | `install.sh` | ✅ Completo |

### O que ainda falta (DoDs operacionais)

| Item | Prioridade |
| --- | --- |
| Piloto real — rodar em 5+ PRs de um time | 🔴 Alta |
| Coletar feedback dos devs em `FEEDBACK.md` | 🔴 Alta |
| Calibrar thresholds com base no feedback real | 🟠 Média |
| Validação scripts dos 5 agentes não-security (além de security) | 🟡 Baixa — já existem, precisam de testes unitários dedicados |

---

## Arquitetura em 3 repos

```
trust/          ← este repo — framework + skills + core
  └── instala em ~/.trust/

setup-repo/     ← por time — config + grounding + checklists
  ├── trust.config.yaml
  ├── grounding/
  └── checklists/

product-repo/   ← repo do produto — ZERO pegada do TRUST
```

---

## Como continuar o desenvolvimento

### Próxima sessão — piloto real

1. Criar `setup-repo` para um time usando `/trust init pilot`
2. Rodar `/trust review-pr` em 5 PRs reais
3. Preencher `FEEDBACK.md` com achados do piloto
4. Rodar `/trust learn from-history` para propor calibrações
5. Aplicar calibrações com `/trust learn apply`

### Referências

- [README.md](README.md) — visão geral e TL;DR
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — roadmap completo com DoDs
- [CHANGELOG.md](CHANGELOG.md) — histórico de versões
- [docs/03-onboarding.md](docs/03-onboarding.md) — guia de instalação passo a passo

---

## Decisões de design (não reverter sem ADR)

| Decisão | Racional |
| --- | --- |
| **Modo estrito por padrão** — HALT em qualquer DoD falho | Falha silenciosa é pior que HALT visível |
| **Repo do produto 100% limpo** (Pilot mode) | Zero resistência política |
| **IA nunca aprova nem rejeita** | Pilar 5 irrevogável |
| **Precision > Recall** — limiar 0.80 | Um falso positivo destrói confiança permanentemente |
| **evidence_quote literal obrigatório** | Paráfrase é hallucination |
| **Grounding first, sempre** | Sem contexto do projeto, a IA usa conhecimento genérico |
| **Sources plugáveis desde o início** | Não travar adoção em empresas com Confluence/Notion |
| **Python para scripts** | Aderência à spec agentskills.io, sem dependências pesadas |

---

*TRUST v2.1.0 · MIT License · 2026-05-18*
