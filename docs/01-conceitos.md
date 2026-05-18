# Conceitos — TRUST

> **Pergunta que este doc responde:** o que é o TRUST conceitualmente, qual problema ele resolve, e quais são as ideias-mãe que sustentam o framework.

---

## 1. O problema central

Times que adotam AI code review tipicamente abandonam a ferramenta em 3-4 sprints. Os sintomas se repetem:

- **Falsos positivos** — a IA aponta como "bug" coisas que são padrão do projeto
- **Hallucinations** — cita arquivos/linhas que não existem
- **Sem cobertura mensurável** — ninguém sabe se a IA checou *tudo* ou só amostragem
- **Sem rastreabilidade** — não dá pra dizer "essa regra existe porque o ADR-007 do projeto exige"
- **Prompt genérico** — um único agente tentando revisar tudo

A consequência é previsível: o time desliga a integração. O custo do ruído supera o valor dos achados reais.

**TRUST nasce dessa observação.** A tese: review confiável não é sobre "ter uma IA melhor". É sobre **forçar a IA a operar dentro das regras do SEU projeto, com cobertura verificável**.

---

## 2. Os 7 Pilares

O framework é organizado em torno de sete pilares. Cada pilar resolve um sintoma específico do "review de IA que devs ignoram". Os sete juntos formam a tese completa.

### Pilar 1 — Especialização

> Seis agentes focados, não um genérico.

Cada agente cobre **um domínio** (segurança, contratos, dados, performance, convenções, testes). Ele carrega **apenas** seu próprio `SKILL.md` e checklist — não conhece o trabalho dos outros agentes. Isso evita o problema do prompt genérico onde um único agente tenta vigiar tudo e termina vigiando nada bem.

### Pilar 2 — Grounding

> Sem docs do projeto, sem review.

Antes de qualquer agente tocar no diff, ele é **obrigado a carregar 7+ documentos do projeto**: arquitetura, glossário de domínio, contratos de API, modelo de dados, convenções, política de segurança, ADRs. Se algum doc obrigatório faltar, o framework HALTA. A regra é simples: **a IA nunca usa "conhecimento geral" — só usa as regras do projeto**.

### Pilar 3 — Second Pass

> Re-leitura honesta do diff.

Depois de produzir os findings, cada agente re-lê o diff inteiro e justifica **o que NÃO reportou**. Cada hunk do diff precisa ter um de dois destinos: virou finding OU foi explicitamente clareado com justificativa. Hunks sem destino → HALT. Isso combate a "preguiça do LLM" de reportar 3 coisas óbvias e ignorar o resto.

### Pilar 4 — Precision Gate

> Em caso de dúvida, não reporta.

Findings com `confidence < 0.80` são movidos para um anexo silenciado. Não somem (auditoria preserva), mas não aparecem no review principal. A regra: **cry wolf é pior que omissão**. Reportar errado destrói confiança; omitir um item duvidoso preserva. O time pode ajustar o threshold no `config.yaml`.

### Pilar 5 — Human-in-the-Loop

> A IA nunca aprova nem rejeita.

O framework gera um `REVIEW.md` com findings sugeridos. **O dev decide** com três botões conceituais: 👍 (aceita), ✏️ (edita), fix (corrige). Não existe modo "auto-merge" no TRUST. Toda decisão final é humana, e essa é uma escolha de design não-negociável.

### Pilar 6 — Rastreabilidade

> Toda regra tem um endereço.

Cada finding carrega obrigatoriamente:
- `rule_id` — identificador único (ex: `SEC-007`)
- `rule_source` — caminho que aponta para a seção do grounding que justifica a regra

Se uma regra não tem `rule_source` apontando para o grounding, ela **não existe** para o framework. Isso garante que toda objeção é defensável e auditável.

### Pilar 7 — Meta-Review

> IA revisando a IA.

Um agente dedicado caça invenções dos outros agentes. Para cada finding, valida quatro coisas:
1. O arquivo citado existe no diff?
2. A linha citada existe no diff?
3. O `evidence_quote` é **literal** ao código (caractere a caractere)?
4. O `rule_source` aponta para uma seção que existe no grounding?

Falhou qualquer um → finding é descartado e registrado como hallucination interceptada. **Phantom imports, dead code, assinaturas inventadas morrem aqui.**

---

## 3. Profiles operacionais

TRUST não é "one size fits all". Existem **quatro profiles** que pré-configuram o framework para cenários diferentes:

### Profile **Pilot** ★ (recomendado para começar)

> Um time piloto numa empresa grande, sem standards corporativos prontos para consumir.

- Setup vive em **repo separado** do produto
- Config, grounding, checklists e skills versionados no setup repo
- Repo do produto fica **100% limpo** (zero pegada do framework)
- Vinculação por env var `TRUST_SETUP_PATH`
- Quando outros times se interessam, eles forkam o setup repo

Este é o profile que a maioria dos primeiros adotantes deveria usar. Veja **[docs/02-arquitetura.md](02-arquitetura.md)**.

### Profile **Team**

> Time inteiro de um repo, versionar o framework junto com o código.

- Tudo (config, grounding, skills) vive em `.review/` e `.claude/skills/` **dentro** do repo do produto
- Mudanças nas regras passam por PR junto com mudanças de código
- Recomendado quando o time é dono soberano do repo e não há preocupação com "poluição"

### Profile **Solo**

> Dev sozinho, second brain como fonte primária.

- Grounding vive em vault Obsidian/Notion pessoal
- Config não fica versionado no repo (`.env.local` + `.gitignore`)
- Mesmas regras servem múltiplos projetos do dev
- Recomendado para consultores, freelancers, devs de produto solo

### Profile **Enterprise**

> Empresa grande com standards corporativos consolidados.

- **Três camadas de grounding**: corporativa, time, pessoal
- Camadas têm prioridade hierárquica explícita
- Overrides são auditáveis (cada finding mostra `provenance`)
- Recomendado quando já existe um time de plataforma mantendo standards globais

---

## 4. A tríade SKILL + Checklist + Grounding

Cada domínio (security, contracts, etc) tem três artefatos que se referenciam mutuamente:

| Artefato | Pergunta que responde | Onde mora |
| --- | --- | --- |
| **SKILL.md** | *Como* o agente opera | `skills/<dominio>/SKILL.md` |
| **checklist** | *O quê* avaliar (regras numeradas) | `checklists/<dominio>.checklist.md` |
| **grounding** | *Por quê* essas regras existem | `grounding/06-security-policy.md` |

Sem qualquer um dos três, o agente não funciona. Eles formam uma tríade que se valida mutuamente — o SKILL aponta para o checklist, o checklist aponta para o grounding, e cada finding produzido cita os três.

---

## 5. Filosofia: Definition of Done estrito

O TRUST opera em **modo estrito**. Cada fase do framework tem critérios objetivos de "estou pronta" — não "o agente disse que terminou". Se uma fase não atinge seus critérios:

1. O framework **PARA**
2. Os artefatos da run são **preservados** em `.review/runs/<run-id>/`
3. Um marker `.trust-halt` é criado avisando o dev
4. O dev investiga, corrige, e executa novamente

Esse design existe para resolver o medo legítimo de "deixar coisa pra trás". Sem DoD, o LLM declara vitória cedo demais.

Detalhes dos DoDs por fase em **[docs/02-arquitetura.md](02-arquitetura.md#dods-por-fase)**.

---

## 6. O que TRUST NÃO é

Para evitar confusão, vale dizer o que está fora do escopo:

- **Não é um linter** — não substitui ESLint, Pylint, gofmt
- **Não é um SAST** — não substitui Snyk, Semgrep, CodeQL
- **Não é um CI/CD** — não substitui GitHub Actions ou GitLab CI
- **Não é uma ferramenta de auto-merge** — a IA nunca decide

TRUST **complementa** essas ferramentas. Ele revisa o que linters e SASTs não veem: as **regras do projeto** que existem em documentos e na cabeça do time, mas não em um arquivo `.eslintrc`.

---

**Próximo:** [docs/02-arquitetura.md](02-arquitetura.md) — como tudo isso se materializa em pastas, arquivos e fluxo de execução.
