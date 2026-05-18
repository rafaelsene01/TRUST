# Plano de Implementação — TRUST

> **Pergunta que este doc responde:** o que vai ser construído, em que ordem, e como sei que cada fase está pronta.

---

## Filosofia do plano

O plano segue 4 princípios:

1. **Cada fase tem um DoD verificável** — não "achismo de pronto"
2. **MVP funciona end-to-end mesmo que mínimo** — preferimos profundidade vertical (1 agente completo) a largura horizontal (6 agentes pela metade)
3. **Cada fase entrega valor independente** — se pararmos no v1.0, o time piloto já tem benefício real
4. **Versionamento semântico** — MVP, v1.0, v1.1, v1.2 são releases reais, marcadas com git tag

---

## Mapa geral das fases

| Fase | Nome | Foco | Estimativa\* |
| --- | --- | --- | --- |
| **MVP** | Vertical Slice | 1 agente completo, fluxo end-to-end | 2-3 sprints |
| **v1.0** | Pilot Ready | 6 agentes + 8 fases completas | 3-4 sprints |
| **v1.1** | Sources & UX | Notion/HTTP adapters + DX | 2 sprints |
| **v1.2** | Rastreabilidade | Jira/Spec integration | 1-2 sprints |
| **v2.0** | Multi-Profile | Team/Solo/Enterprise profiles | 3-4 sprints |
| **v2.1** | Learning Loop | Auto-improvement de checklists | 2-3 sprints |

\* Estimativas em sprints de 2 semanas, time de 2-3 devs part-time. Ajuste para sua realidade.

---

## Fase MVP — Vertical Slice

**Objetivo:** rodar o primeiro review real, end-to-end, com **um único agente funcionando**. Sem isso, todo o resto é teoria.

### Escopo do MVP

✅ Incluído:
- 1 agente: `trust-security-review` (escolhido por ser o mais valioso para começar)
- Adapter `filesystem` apenas (Notion/HTTP ficam para v1.1)
- Profile `pilot` apenas (outros profiles ficam para v2.0)
- 5 das 8 fases: Trigger, Grounding, Agente, Precision Gate, Output
- Slash commands: `/trust init pilot`, `/trust review-pr`, `/trust doctor`
- Output local em `REVIEW.md` (sem comentário em PR ainda)

❌ Fora do MVP (vai pra v1.0+):
- Second Pass (Fase 3)
- Meta-Review (Fase 5)
- Rastreabilidade (Fase 6)
- Os outros 5 agentes
- Adapters Notion e HTTP
- `/trust map codebase`
- `/trust approve-drafts`
- Postagem automática em PR

### Entregáveis do MVP

| # | Entregável | Path |
| --- | --- | --- |
| 1 | Skill `trust-security-review` completa | `skills/trust-security-review/` |
| 2 | Core: orchestrator + grounding_loader + halt_handler | `core/` |
| 3 | Adapter filesystem | `adapters/filesystem_adapter.py` |
| 4 | Slash commands base | `commands/` |
| 5 | Templates de config e target | `templates/` |
| 6 | Script de install | `install.sh` |
| 7 | Skill validada com `skills-ref validate` | — |
| 8 | Teste end-to-end com repo-mock | `tests/e2e/mvp_test.py` |

### Definition of Done — MVP

**Para fechar o MVP, TODOS estes critérios precisam estar verdes:**

#### DoD funcional
- [ ] `/trust init pilot` cria setup repo com estrutura correta
- [ ] `/trust doctor` valida env var + sources + skills
- [ ] `/trust review-pr` executa as 5 fases sem erro em diff de exemplo
- [ ] Agente security produz `coverage.json` com 100% das regras avaliadas
- [ ] Findings têm `rule_id`, `rule_source`, `evidence_quote` literal e `confidence`
- [ ] Precision Gate separa findings ≥ 0.80 dos < 0.80
- [ ] `REVIEW.md` gerado em `${TRUST_REVIEW_OUTPUT}/...`
- [ ] HALT funciona: rodar com grounding incompleto → para na Fase 1

#### DoD de qualidade
- [ ] `skills-ref validate skills/trust-security-review/` passa
- [ ] `SKILL.md` < 500 linhas, < 5000 tokens
- [ ] Todos os scripts Python têm type hints e exit codes documentados
- [ ] Teste end-to-end roda em < 60s
- [ ] Zero erros em `python -m mypy` no `core/`

#### DoD de documentação
- [ ] README atualizado com badge "Status: MVP shipped"
- [ ] `docs/03-onboarding.md` atualizado com instruções reais do MVP
- [ ] `CHANGELOG.md` criado com entrada `## [MVP] - <data>`
- [ ] Tag `v0.1.0-mvp` no git

### Como validar o MVP

```bash
# Teste manual end-to-end
git clone github.com/seu-user/trust ~/.trust
cd ~/.trust && ./install.sh

# Criar repo mock
mkdir -p /tmp/trust-mvp-test/{mock-product,mock-setup}
cd /tmp/trust-mvp-test/mock-setup
/trust init pilot
# preencher prompts apontando para ../mock-product

# Adicionar um bug óbvio no mock-product
cd ../mock-product
echo 'const q = `SELECT * FROM users WHERE email='\''${email}'\''`' > src/sql_inject.ts
git add . && git commit -m "test: bug óbvio"

# Rodar review
export TRUST_SETUP_PATH=/tmp/trust-mvp-test/mock-setup
/trust review-pr

# Validações:
# 1. REVIEW.md gerado
# 2. Pelo menos 1 finding emitido (o SQL injection)
# 3. Finding tem rule_id SEC-* e evidence_quote literal
# 4. Sem erros no output
```

---

## Fase v1.0 — Pilot Ready

**Objetivo:** o framework está **pronto para o piloto real** num time. Todas as 8 fases funcionam, todos os 6 agentes ativos.

### Escopo do v1.0

✅ Adicionado em relação ao MVP:
- 5 agentes restantes: contracts, data, performance, conventions, tests
- Fase 3: Second Pass
- Fase 5: Meta-Review (anti-hallucination)
- Fase 6: Rastreabilidade (modo desativado por padrão, mas funcional)
- `/trust map codebase` para bootstrap brownfield
- `/trust approve-drafts` para revisão dos drafts
- `/trust cleanup <run-id>` para limpar runs
- Política de retenção de runs (`audit_failures_only` como default)

### Entregáveis do v1.0

| # | Entregável | Path |
| --- | --- | --- |
| 1 | 5 skills adicionais | `skills/trust-{contracts,data,performance,conventions,tests}-review/` |
| 2 | Skill Second Pass | `skills/trust-second-pass/` |
| 3 | Skill Meta-Review | `skills/trust-meta-review/` |
| 4 | Comando `/trust map codebase` | `commands/trust-map.md` + `core/codebase_mapper.py` |
| 5 | Comando `/trust approve-drafts` | `commands/trust-approve-drafts.md` |
| 6 | Comando `/trust cleanup` | `commands/trust-cleanup.md` |
| 7 | Logic de retention policy | `core/run_lifecycle.py` |
| 8 | Suite de testes E2E expandida | `tests/e2e/` |

### Definition of Done — v1.0

#### DoD funcional
- [ ] Todos os 6 agentes produzem findings válidos em repo de exemplo
- [ ] Fase Second Pass detecta hunks não revisados e dispara HALT
- [ ] Fase Meta-Review intercepta hallucinations injetadas em teste
- [ ] `/trust map codebase` gera drafts em `_drafts/` corretamente
- [ ] `/trust approve-drafts` move arquivos de `_drafts/` para `grounding/`
- [ ] Política `audit_failures_only` apaga JSONs em sucesso, mantém em halt
- [ ] Run-manifest valida contadores cruzados entre fases (Fase 7 DoD)

#### DoD de qualidade
- [ ] Todas as 9 skills passam em `skills-ref validate`
- [ ] Coverage de testes > 70% em `core/`
- [ ] Documentação de cada skill (`references/*.md`) revisada por pelo menos 1 dev
- [ ] Performance: review de PR com 50 arquivos termina em < 5 minutos

#### DoD de adoção
- [ ] Pelo menos 1 time piloto rodou TRUST em 5 PRs reais
- [ ] Feedback coletado em `FEEDBACK.md`
- [ ] Calibração inicial dos thresholds com base no feedback
- [ ] Tag `v1.0.0` no git

---

## Fase v1.1 — Sources & UX

**Objetivo:** abrir as portas para grounding em **fontes não-filesystem** e polir a experiência do dev.

### Escopo do v1.1

✅ Adicionado:
- Adapter `notion` (lê páginas e databases do Notion)
- Adapter `http` (Confluence/Wiki autenticado)
- Suporte a `volatile: true` em sources externas
- Melhorias de UX:
  - Progress bar nas fases longas
  - Mensagens de erro acionáveis ("rode `/trust doctor` para corrigir")
  - `--verbose` flag em todos os comandos
  - `/trust runs list` para ver histórico
  - `/trust runs show <id>` para inspecionar um run

### Entregáveis do v1.1

| # | Entregável | Path |
| --- | --- | --- |
| 1 | Adapter Notion completo | `adapters/notion_adapter.py` |
| 2 | Adapter HTTP completo | `adapters/http_adapter.py` |
| 3 | Cache de sources externas | `core/source_cache.py` |
| 4 | Comando `/trust runs` | `commands/trust-runs.md` |
| 5 | Progress reporter | `core/progress_reporter.py` |
| 6 | Docs atualizados | `docs/02-arquitetura.md`, `docs/03-onboarding.md` |

### Definition of Done — v1.1

- [ ] Notion adapter lê databases e páginas corretamente
- [ ] HTTP adapter autentica via token de env var
- [ ] Cache TTL respeitado (default 60min)
- [ ] Sources `volatile` não disparam HALT em hash mismatch
- [ ] Mensagens de erro têm sempre uma "próxima ação" sugerida
- [ ] Progress bar funcional para fases > 30s
- [ ] Tag `v1.1.0` no git

---

## Fase v1.2 — Rastreabilidade

**Objetivo:** ligar findings a tickets Jira e spec files (Pilar 6).

### Escopo do v1.2

✅ Adicionado:
- Integração Jira (REST API + branch pattern matching)
- Spec files (`.spec.md`) — convenção e parser
- Campo `traced_to` em cada finding
- Anexo de rastreabilidade no `REVIEW.md`
- Comando `/trust trace check` para validar rastreabilidade sem rodar review completo

### Entregáveis do v1.2

| # | Entregável | Path |
| --- | --- | --- |
| 1 | Jira integration | `core/jira_integration.py` |
| 2 | Spec file parser | `core/spec_parser.py` |
| 3 | Comando `/trust trace check` | `commands/trust-trace.md` |
| 4 | Template de `.spec.md` | `templates/spec.md.template` |

### Definition of Done — v1.2

- [ ] Jira API lê tickets via `branch_pattern` matching
- [ ] Findings recebem `traced_to: {jira_id, spec_path?}`
- [ ] Findings sem trace ganham `untraceable_reason` registrado
- [ ] `REVIEW.md` tem anexo "Rastreabilidade" quando enabled
- [ ] Tag `v1.2.0` no git

---

## Fase v2.0 — Multi-Profile

**Objetivo:** suportar oficialmente os profiles `team`, `solo` e `enterprise`, além do `pilot`.

### Escopo do v2.0

✅ Adicionado:
- Profile `team`: tudo dentro do repo do produto, sem setup repo separado
- Profile `solo`: second brain como source primária, `.env.local` em vez de repo
- Profile `enterprise`: hierarquia de camadas (corp/team/personal) com override policy
- Campo `provenance` em findings (Enterprise)
- `/trust init` interativo escolhe o profile

### Entregáveis do v2.0

| # | Entregável | Path |
| --- | --- | --- |
| 1 | Profile registry e validators | `core/profile_registry.py` |
| 2 | Layer resolver (Enterprise) | `core/layer_resolver.py` |
| 3 | Provenance tracker | `core/provenance.py` |
| 4 | Templates por profile | `templates/profiles/{team,solo,enterprise}/` |
| 5 | Migration script (pilot → enterprise) | `scripts/migrate_pilot_to_enterprise.py` |

### Definition of Done — v2.0

- [ ] Os 4 profiles funcionam end-to-end em testes E2E
- [ ] Override policy do Enterprise é auditável (cada override tem reason)
- [ ] Migration script testado em repo real
- [ ] Documentação dos 4 profiles em `docs/01-conceitos.md`
- [ ] Tag `v2.0.0` no git

---

## Fase v2.1 — Learning Loop

**Objetivo:** o framework aprende com os reviews passados e propõe novas regras.

### Escopo do v2.1

✅ Adicionado:
- `/trust learn from-history` — lê histórico de PRs e propõe regras candidatas
- Score de "false positive rate" por regra ao longo do tempo
- Sugestão automática de ajuste de threshold
- Dashboard `/trust stats` com métricas do time

### Entregáveis do v2.1

| # | Entregável | Path |
| --- | --- | --- |
| 1 | Histórico de findings consolidado | `core/findings_history.py` |
| 2 | Sugestor de regras candidatas | `core/rule_suggester.py` |
| 3 | Comando `/trust learn` | `commands/trust-learn.md` |
| 4 | Comando `/trust stats` | `commands/trust-stats.md` |

### Definition of Done — v2.1

- [ ] `/trust learn from-history` analisa pelo menos 50 PRs e propõe ≥ 1 regra
- [ ] False positive rate calculado por regra (`team_calibration.json`)
- [ ] Sugestões de threshold registradas em `runs/learning/`
- [ ] Dashboard exporta JSON + Markdown
- [ ] Tag `v2.1.0` no git

---

## Dependências entre fases

```
MVP ──→ v1.0 ──→ v1.1 ──→ v1.2 ──→ v2.0 ──→ v2.1
         │
         └──→ pode pular v1.1/v1.2 e ir direto pra v2.0 se necessário
```

- **MVP** é pré-requisito absoluto de todas as outras
- **v1.0** é pré-requisito de v2.0 (multi-profile precisa dos 6 agentes)
- **v1.1** e **v1.2** são paralelizáveis se houver time

---

## Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
| --- | --- | --- | --- |
| Drafts do `/trust map` ficam genéricos | Alta | Alto | Forçar revisão humana antes de aprovar; gerar com prompts específicos por stack |
| Coverage 100% gera HALT excessivo no início | Alta | Médio | Começar com checklists pequenos (5-10 regras), expandir gradualmente |
| Adoção dos outros devs do time | Média | Alto | DX impecável: doctor com fixes acionáveis, mensagens claras, < 5min até primeiro review |
| Notion API rate limit | Baixa | Médio | Cache agressivo + retry com backoff |
| Performance em PRs grandes | Média | Médio | Paralelização dos 6 agentes; limite configurável de hunks/run |
| Falsa percepção de "auto-aprovação" | Média | Crítico | Nunca remover o princípio "humano decide"; documentar em todo lugar |

---

## Métricas de sucesso

Como saber se o TRUST está funcionando no piloto:

| Métrica | Meta v1.0 | Meta v2.0 |
| --- | --- | --- |
| **Adoção** | 80% dos PRs do time piloto passam pelo TRUST | 60% dos PRs de 3+ times |
| **Precisão** | < 20% false positive rate | < 10% |
| **Confiança** | NPS dos devs ≥ 7/10 | ≥ 8/10 |
| **Hallucinations** | < 1 por 100 findings interceptadas | < 1 por 500 |
| **Time-to-review** | < 5 min para PR de 50 arquivos | < 3 min |
| **HALT rate** | < 5% das runs | < 2% |

---

## Próximo passo concreto

**Onde estamos agora:** desenho conceitual completo, primeira skill (`trust-security-review`) refatorada na spec agentskills.io.

**O que fazer a seguir, em ordem:**

1. ✅ Criar repo `trust` no GitHub com a estrutura definida
2. ⬜ Implementar `core/orchestrator.py` mínimo (carregar config, capturar diff)
3. ⬜ Implementar `adapters/filesystem_adapter.py`
4. ⬜ Implementar `core/grounding_loader.py` usando o adapter
5. ⬜ Escrever 5-10 regras no `security.checklist.md` de exemplo
6. ⬜ Escrever 3-5 grounding docs de exemplo
7. ⬜ Implementar o agente security usando a skill já refatorada
8. ⬜ Wire-up de slash commands `/trust init` e `/trust review-pr`
9. ⬜ Teste E2E com repo mock
10. ⬜ Tag `v0.1.0-mvp`

---

**Voltar:** [README.md](README.md) · [docs/01-conceitos.md](docs/01-conceitos.md)
