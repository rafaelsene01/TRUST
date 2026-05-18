# Glossário — TRUST

> **Pergunta que este doc responde:** o que cada termo significa no contexto do TRUST.

Organizado alfabeticamente para consulta rápida.

---

### Adapter

Componente plugável que implementa o contrato de leitura de uma **source** de grounding. O TRUST inclui adapters para `filesystem`, `notion` e `http` (Confluence/Wiki). Veja [docs/02-arquitetura.md](02-arquitetura.md#3-sources-plugáveis-sistema-de-adapters).

### Agente especialista

Um dos 6 agentes do Pilar 1 (security, contracts, data, performance, conventions, tests). Cada agente carrega **apenas** seu próprio `SKILL.md` e checklist, sem conhecer o trabalho dos outros agentes.

### Camada (layer)

No profile **Enterprise**, o grounding é organizado em camadas com prioridade hierárquica (corp, team, personal). Camadas mais específicas podem sobrescrever camadas mais base, com auditoria de proveniência.

### Checklist

Arquivo `<dominio>.checklist.md` no setup repo, contendo a lista numerada de regras do projeto para um domínio. Cada regra tem um `rule_id` único. É o "o quê" da tríade SKILL + checklist + grounding.

### Confidence

Número entre 0.0 e 1.0 que cada finding carrega obrigatoriamente. Findings com `confidence < 0.80` são silenciados pela Fase 4 (Precision Gate). Threshold configurável no `trust.config.yaml`.

### Coverage matrix

Matriz produzida por cada agente na Fase 2: para cada combinação **regra × arquivo do diff**, um veredito (`compliant`, `violation`, ou `not_applicable` com justificativa). Sem 100% de cobertura → HALT.

### Cry wolf

Antipattern em AI review: emitir muitos alertas de baixa qualidade, levando o time a ignorar **todos** os alertas — inclusive os reais. O TRUST combate via Precision Gate (Pilar 4): "melhor não reportar do que reportar errado".

### Definition of Done (DoD)

Critérios objetivos que cada fase precisa atender para ser considerada "concluída". DoDs falhos disparam HALT no modo estrito. Detalhes em [docs/02-arquitetura.md](02-arquitetura.md#2-as-8-fases-de-execução).

### Drafts (`_drafts/`)

Versões iniciais dos grounding docs geradas pelo `/trust map codebase`. **Drafts não são fonte de verdade** — precisam ser revisados e aprovados pelo time antes de virarem `grounding/<doc>.md`.

### Evidence quote

Trecho **literal** (copy-paste, caractere-a-caractere) do código que serve como evidência de um finding. Parafrasear é proibido. A Fase 5 (Meta-Review) valida que o quote bate exatamente com o código no diff.

### Finding

Objeto JSON produzido por um agente quando encontra uma violação de regra. Contém obrigatoriamente: `agent`, `rule_id`, `rule_source`, `file`, `line_start/end`, `severity`, `confidence`, `claim`, `evidence_quote`, `why_it_matters`, `suggestion`, `false_positive_risk`.

### Framework TRUST (Repo 1)

Repositório que contém o **motor** do TRUST: skills, commands, adapters, core, templates. Distribuído como plugin do Claude Code. Instalado uma vez por máquina.

### Grounding

Os 7+ documentos do projeto que servem como **fonte de verdade** para os agentes (arquitetura, glossário de domínio, contratos, modelo de dados, convenções, política de segurança, ADRs). Sem grounding completo → HALT.

### HALT

Comportamento do modo estrito: quando qualquer DoD de qualquer fase falha, o framework **para imediatamente**, preserva todos os artefatos da run, cria marker `.trust-halt`, e exige intervenção do dev.

### Hallucination

Quando a IA inventa informação que não existe na realidade: cita arquivo inexistente, linha que não está no diff, parafraseia código como se fosse literal, ou referencia regra que não está no grounding. A Fase 5 (Meta-Review) intercepta hallucinations.

### Hunk

Bloco contíguo de mudanças em um diff (formato unified diff). Na Fase 3 (Second Pass), cada hunk do diff precisa ter um destino: virou finding OU foi clareado com justificativa. Hunks "unaccounted" → HALT.

### Meta-Review

Pilar 7 e Fase 5 do framework. Agente dedicado a validar a realidade de cada finding (4 checks). Findings que falham qualquer check vão para anexo `hallucinations_caught`.

### Override (regras)

No profile Enterprise, quando uma camada mais específica (ex: team) define uma regra que conflita com camada mais base (ex: corp). Cada override é auditável e exige razão registrada no finding (`provenance.override_reason`).

### Precision Gate

Pilar 4 e Fase 4 do framework. Filtra findings por `confidence`. Padrão: ≥ 0.80 passa, < 0.80 vai para anexo silenciado.

### Profile

Modelo operacional do TRUST. Quatro profiles: `pilot` (recomendado), `team`, `solo`, `enterprise`. Cada profile pré-configura sources, layers e defaults sensatos. Detalhes em [docs/01-conceitos.md](01-conceitos.md#3-profiles-operacionais).

### Provenance

Metadados de um finding indicando de qual camada (`layer`) ele veio, e se sobrescreveu uma regra de camada mais base. Usado para auditoria no profile Enterprise.

### Run

Uma execução do `/trust review-pr`. Cada run tem um `run-id` único e produz uma pasta em `runs/<run-id>/` com todos os artefatos intermediários.

### Run manifest

Arquivo `run-manifest.json` no topo da pasta da run. Rastreia status de cada fase, DoD passado/falho, timestamps e blockers.

### Rule ID

Identificador único de uma regra do checklist (ex: `SEC-007`, `PERF-012`). Findings sem `rule_id` são inválidos.

### Rule source

Caminho no formato `<source-id>:<path>#<section>` apontando para a seção do grounding que justifica uma regra. Findings sem `rule_source` válido são inválidos.

### Second Pass

Pilar 3 e Fase 3 do framework. Cada agente re-lê o diff e justifica explicitamente o que NÃO reportou. Combate a "preguiça do LLM".

### Setup repo (Repo 2)

Repositório do time piloto contendo config, grounding, checklists, skills customizadas e targets. Vive **separado** do repo do produto. Vinculado via env var `TRUST_SETUP_PATH`.

### Severity

Atributo de finding indicando gravidade: `critical`, `high`, `medium`, `low`. Independente de `confidence` — um finding pode ser `critical` mas com confiança baixa (caso típico de silenciamento).

### Silenced (findings)

Findings que passaram pelo Precision Gate mas não atingiram o threshold de confiança. Ficam em anexo do `REVIEW.md`, não no corpo principal. Auditáveis mas não geram ruído.

### SKILL.md

Arquivo central de cada skill, com YAML frontmatter (`name`, `description`, etc) e instruções em Markdown. Segue a spec **[agentskills.io](https://agentskills.io/specification)**. Detalhes em [docs/04-skills-spec.md](04-skills-spec.md).

### Source (grounding source)

Configuração no `trust.config.yaml` declarando de onde um doc de grounding deve ser lido (filesystem, Notion, http). Sources podem ser **volatile** (hash não bloqueia HALT).

### Strict mode

Modo padrão do TRUST onde qualquer DoD falho dispara HALT. Configurável via `framework.mode` no `trust.config.yaml`, mas mudar para warn-only **não é recomendado**.

### Target

Arquivo `targets/<repo>.yaml` no setup repo, definindo como o setup revisa um repo-alvo específico (stack, agentes aplicáveis, overrides, política de comentário em PR).

### Tríade SKILL + Checklist + Grounding

A unidade fundamental de cada domínio do TRUST. Os três artefatos se referenciam mutuamente: SKILL aponta para checklist, checklist aponta para grounding, cada finding cita os três.

### `TRUST_SETUP_PATH`

Variável de ambiente que aponta para o setup repo. **A única ponte** entre o framework instalado, o setup do time, e o repo do produto.

### Volatile (source)

Atributo de uma source indicando que seu conteúdo muda frequentemente (típico de second brain do dev). Hash da fase 1 é apenas logado, não bloqueia HALT.

---

**Voltar ao início:** [README.md](../README.md)
