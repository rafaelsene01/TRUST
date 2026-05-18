# TRUST

> **Trustable Reviews via Universal Skills & Tooling**
> *O review de IA em que dá pra confiar.*

[![Profile](https://img.shields.io/badge/profile-pilot-orange)](docs/01-conceitos.md#profiles)
[![Spec](https://img.shields.io/badge/spec-agentskills.io-blue)](https://agentskills.io/specification)
[![Status](https://img.shields.io/badge/status-MVP%20shipped-brightgreen)](CHANGELOG.md)

TRUST é um **framework de review de Pull Requests com agentes de IA**, baseado em sete pilares que separam um review confiável de um que devs ignoram. Ele roda local no Claude Code, é agnóstico de stack, e vive **desacoplado do repo do produto**.

---

## TL;DR

- 🎯 **6 agentes especialistas** (segurança, contratos, dados, performance, convenções, testes) — sem prompt genérico
- 📚 **Grounding obrigatório**: o agente lê 7+ docs do projeto antes de tocar no diff
- ✅ **Definition of Done estrito** por fase: cobertura < 100% ou confiança < 80% **HALTA** a execução
- 🔍 **Anti-hallucination**: meta-reviewer valida cada finding contra o diff real
- 🧼 **Repo do produto fica limpo**: zero pegada do framework no código do produto
- 🧩 **Sources plugáveis**: grounding pode vir de filesystem, Notion, Confluence ou second brain
- 👤 **Humano sempre decide**: IA sugere, dev aprova com 👍 / ✏️ / fix

---

## Para quem é

TRUST é para times que **já tentaram AI code review e desistiram**. Os sintomas conhecidos:

> "A IA aponta coisas que contradizem nossos ADRs."
> "70% dos alertas são ruído — a gente ignorou tudo."
> "Ela inventa imports e cita linhas que não existem."
> "Não temos como saber se o review checou *tudo*."

Se você reconhece pelo menos dois desses, TRUST foi desenhado para você.

---

## Como funciona em 30 segundos

```bash
# 1. Instala o framework (uma vez por máquina)
/plugin add github.com/seu-user/trust

# 2. Clona o setup do seu time (uma vez por dev)
git clone github.com/empresa/payments-team-trust ~/work/payments-team-trust
export TRUST_SETUP_PATH=~/work/payments-team-trust

# 3. Trabalha no repo do produto normalmente, sem alterações
cd ~/work/api-payments
git checkout -b feat/PAY-123

# 4. Roda o review
/trust review-pr feat/PAY-123
```

O framework auto-descobre o setup pela env var, casa o repo atual com um `target.yaml`, carrega o grounding, executa as 8 fases com DoD estrito, e gera um `REVIEW.md` **fora do repo do produto**.

Detalhes em **[docs/03-onboarding.md](docs/03-onboarding.md)**.

---

## Arquitetura em 3 repos

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│ 1. Framework TRUST  │    │ 2. Setup do Time ★   │    │ 3. Repo do Produto  │
│   (este repo)       │ ─→ │  payments-team-trust │ ─→ │   api-payments      │
│   o motor           │    │  config + regras     │    │   100% LIMPO        │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
       instalado uma vez       clonado uma vez          nunca tocado pelo TRUST
```

Vinculação por uma única env var (`TRUST_SETUP_PATH`). Detalhes em **[docs/02-arquitetura.md](docs/02-arquitetura.md)**.

---

## Documentação

A fonte da verdade do projeto está organizada por tópico para você navegar pelo que importa agora:

| Doc | Para que serve |
| --- | --- |
| **[docs/01-conceitos.md](docs/01-conceitos.md)** | Os 7 pilares, profiles operacionais (Pilot/Team/Solo/Enterprise), filosofia |
| **[docs/02-arquitetura.md](docs/02-arquitetura.md)** | 3 repos, 8 fases, sources plugáveis, hierarquia de camadas |
| **[docs/03-onboarding.md](docs/03-onboarding.md)** | Instalação, init, doctor, primeiro review passo a passo |
| **[docs/04-skills-spec.md](docs/04-skills-spec.md)** | Como cada skill segue o padrão agentskills.io oficial |
| **[docs/05-glossario.md](docs/05-glossario.md)** | Vocabulário do TRUST (DoD, halt, grounding, target, layer, run-id) |
| **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** | Plano de entrega completo em fases (MVP → v1.0 → v1.x → v2.0) |

---

## Princípios não-negociáveis

Estes princípios estão no DNA do framework. Mudanças que violem qualquer um destes **devem ser rejeitadas**.

1. **A IA nunca aprova nem rejeita um PR.** Apenas sugere.
2. **Sem grounding, sem review.** Se docs obrigatórios faltam, o framework HALTA.
3. **Precision > Recall.** Em caso de dúvida, NÃO reporta. Cry wolf = zero confiança.
4. **Toda regra tem um `rule_id` rastreável** até uma seção do grounding.
5. **Toda evidência é citada literalmente.** Paráfrase nunca.
6. **Cobertura é mensurável.** Matriz regra × arquivo ou HALT.
7. **O dev sempre tem o último botão.**

---

## Status atual

✅ **MVP shipped (`v0.1.0-mvp`).** Pipeline end-to-end funcional com o agente de segurança. Veja o [CHANGELOG](CHANGELOG.md) para o que está incluído e o [plano de implementação](IMPLEMENTATION_PLAN.md) para os próximos marcos.

**Próximo marco:** v1.0 — 5 agentes restantes + Second Pass + Meta-Review completo.

---

## Contribuindo

Por enquanto o framework está em fase de design/MVP. Issues e discussões são bem-vindas. Toda mudança em **regras de grounding, skills, ou DoDs** deve ser feita via PR para manter a auditabilidade.

---

## Licença

MIT — veja [LICENSE](LICENSE).

---

<p align="center">
  <em>"O review de IA em que dá pra confiar."</em>
</p>
