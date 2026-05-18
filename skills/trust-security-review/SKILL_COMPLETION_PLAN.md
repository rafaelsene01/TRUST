# Plano de conclusão — `trust-security-review`

> **Objetivo:** fechar a skill `trust-security-review` no estado "production-ready",
> pronta para ser usada num review real sem supervisão adicional.
>
> **Entregável:** este `.md` é o plano. Os artefatos que ele descreve são produzidos
> em sequência na implementação.

---

## Diagnóstico — onde estamos agora

A skill existe e passou nas validações estruturais da spec agentskills.io (frontmatter,
tamanho, references, scripts, assets). O que foi entregue cobre a estrutura e o contrato.
O que ainda não existe é tudo que faz a skill **funcionar de verdade num review real**:
regras concretas, scripts de suporte, integração real com o diff, e testes da própria skill.

### O que já existe

| Artefato | Estado |
| --- | --- |
| `SKILL.md` | ✅ Completo — frontmatter, escopo, protocolo, golden rules |
| `references/PROTOCOL.md` | ✅ Completo — 8 passos de execução |
| `references/FINDING_FORMAT.md` | ✅ Completo — schema com regras por campo |
| `references/DOD.md` | ✅ Completo — critérios e self-attestation block |
| `references/GOTCHAS.md` | ✅ Completo — edge cases detalhados |
| `assets/finding-template.json` | ✅ Completo — JSON Schema com exemplo |
| `assets/coverage-template.json` | ✅ Completo — JSON Schema com exemplo |
| `scripts/validate_coverage.py` | ✅ Completo — valida cobertura 100% |
| Checklist (`security.checklist.md`) | ⚠️ Existe como template genérico — precisa de regras reais aplicáveis ao projeto |
| `scripts/check_evidence_literal.py` | ❌ Ausente — referenciado no DOD.md mas não criado |
| `scripts/parse_checklist.py` | ❌ Ausente — agente precisa parsear o checklist em estrutura |
| `scripts/validate_dod_attestation.py` | ❌ Ausente — valida o JSON de self-attestation |
| `scripts/check_rule_source.py` | ❌ Ausente — valida que rule_source resolve no grounding |
| Testes da skill isolados | ❌ Ausente — os testes E2E testam o pipeline, não a skill |
| `references/SECOND_PASS.md` | ❌ Ausente — protocolo de Second Pass não documentado na skill |
| `assets/dod-attestation-template.json` | ❌ Ausente — template do bloco de auto-attestation |
| `assets/second-pass-template.json` | ❌ Ausente — formato do non-finding |

### O que está incompleto mas existe

| Artefato | Gap |
| --- | --- |
| `scripts/validate_coverage.py` | Não valida se rule_id existe no checklist; não valida campo `source` por regra |
| `SKILL.md` — seção de exemplos | Mini exemplo só cobre SQLi (SEC-007). Faltam exemplos para secrets, auth, crypto |
| `references/PROTOCOL.md` | Step 7 menciona `scripts/validate_coverage.py` mas não menciona os outros scripts |
| `references/DOD.md` | Menciona `scripts/check_evidence_literal.py` mas o script não existe |
| `references/GOTCHAS.md` | Cobre edge cases de diff e evidência — não cobre edge cases de Second Pass |

---

## Plano de implementação — 5 entregáveis em ordem

```
Entregável 1 → Scripts de suporte (4 scripts Python)
Entregável 2 → Templates de assets ausentes (3 arquivos)
Entregável 3 → Documentação faltante (2 references)
Entregável 4 → Testes isolados da skill (1 arquivo)
Entregável 5 → Integração e revisão final (atualizações)
```

Cada entregável tem um DoD verificável. A skill só está pronta quando todos os 5
passam.

---

## Entregável 1 — Scripts de suporte

**Objetivo:** a skill precisa de 4 scripts Python para que o agente possa executar
validações mecânicas sem depender de raciocínio. Cada script cobre um ponto de
falha documentado no DOD.md ou PROTOCOL.md.

### 1.1 `scripts/check_evidence_literal.py`

**Por quê existe:** o DOD.md exige `every_evidence_quote_literal: true`. O agente
precisa verificar isso mecanicamente — não por raciocínio. Sem o script, o DOD não
é verificável de forma confiável.

**O que faz:** recebe o path do `findings.json` e o path do `diff.patch`. Para cada
finding, confirma que `evidence_quote` aparece literalmente (string contida) no diff.
Retorna exit 0 se todos passam, exit 1 com lista de falhas se algum não passa.

**Interface:**
```
python check_evidence_literal.py <findings.json> <diff.patch>

Exit 0: ✓ All 3 evidence quotes found literally in diff
Exit 1: ✗ Quote not found in diff:
          finding: SEC-007 in src/auth/login.ts
          quote:   "const q = db.query(`SELECT...`)"
          hint:    nearest match at line 42 differs by 2 chars
```

**DoD deste script:**
- Lê findings.json e diff.patch sem dependências externas
- Para cada finding, faz substring search do `evidence_quote` no conteúdo do diff
- Em caso de falha, imprime o quote esperado e onde a busca falhou
- Type hints em todos os parâmetros e retornos
- Exit codes documentados no docstring

---

### 1.2 `scripts/parse_checklist.py`

**Por quê existe:** o PROTOCOL.md Step 2 instrui o agente a "parsear o checklist
em estrutura JSON". Sem um script, o agente parseia manualmente — e varia entre
execuções. Com o script, o parser é determinístico e testável.

**O que faz:** lê `checklists/security.checklist.md` e produz um JSON estruturado
com todos os `rule_id`, `title`, `source`, `severity_default` e `applies_to`.

**Interface:**
```
python parse_checklist.py <path-to-checklist.md> [--output <path.json>]

Saída (stdout ou arquivo):
{
  "total": 12,
  "rules": [
    {
      "rule_id": "SEC-001",
      "title": "No hardcoded secrets in source code",
      "source": "06-security-policy.md#secrets-management",
      "severity_default": "critical",
      "applies_to": "all files"
    },
    ...
  ]
}
```

**DoD deste script:**
- Parseia os 12 `rule_id` do checklist atual sem falhar
- Valida que cada regra tem `rule_id` (formato `SEC-XXX`), `title` não-vazio e
  `source` apontando para seção com `#`
- Falha com exit 1 e mensagem acionável se alguma regra está malformada
- Output é JSON válido e serializável

---

### 1.3 `scripts/validate_dod_attestation.py`

**Por quê existe:** o DOD.md define um bloco JSON de auto-attestation que o agente
deve preencher. Sem validação mecânica, o agente pode declarar `self_check_passed:
true` com campos incorretos. Este script é o gate final antes do orchestrator avançar.

**O que faz:** lê o arquivo `security.dod.json` gerado pelo agente e valida que:
- Todos os campos obrigatórios estão presentes
- Todos os percentuais estão em 100
- Todos os booleans `every_finding_*` são `true`
- `halt_required` é `false`
- `self_check_passed` é `true`

**Interface:**
```
python validate_dod_attestation.py <path-to-security.dod.json>

Exit 0: ✓ DoD attestation valid — self_check_passed: true
Exit 1: ✗ DoD attestation FAILED:
          - rules_evaluated_pct: 87 (expected: 100)
          - every_evidence_quote_literal: false
```

**DoD deste script:**
- Cobre todos os campos definidos no bloco de attestation do DOD.md
- Mensagens de erro indicam exatamente qual campo falhou e qual era o valor recebido
- Aceita o mesmo schema do `assets/dod-attestation-template.json` (Entregável 2)

---

### 1.4 `scripts/check_rule_source.py`

**Por quê existe:** cada finding emitido precisa ter `rule_source` que resolve para
uma seção real no grounding. O meta-reviewer (Fase 5) faz isso no pipeline inteiro,
mas a skill precisa fazer sua própria verificação antes de emitir. Se `rule_source`
aponta para uma seção que não existe, o finding é uma hallucination antes mesmo de
chegar ao meta-reviewer.

**O que faz:** recebe o `findings.json` e o diretório `grounding/`. Para cada
finding, parseia o `rule_source` no formato `<source-id>:<path>#<anchor>`, lê o
arquivo de grounding referenciado, e confirma que o anchor (heading) existe no
documento.

**Interface:**
```
python check_rule_source.py <findings.json> <grounding-dir>

Exit 0: ✓ All 3 rule_sources resolve correctly
Exit 1: ✗ rule_source does not resolve:
          finding: SEC-999 in src/auth/login.ts
          rule_source: "in-setup:06-security-policy.md#nonexistent-section"
          available anchors: input-validation, secrets-management, cryptography, ...
```

**DoD deste script:**
- Parseia o formato `source-id:path#anchor` corretamente
- Lê o arquivo de grounding e extrai heading anchors (mesmo algoritmo do grounding_loader)
- Lista os anchors disponíveis quando o requested não é encontrado (facilita diagnóstico)
- Tolerante a anchors com variações de capitalização (normaliza para lowercase com hífens)

---

## Entregável 2 — Assets ausentes

**Objetivo:** os assets são os templates que o agente carrega on-demand para preencher
estruturas corretas. Dois estão faltando, e um terceiro (dod-attestation) é necessário
para o script do Entregável 1.3 funcionar.

### 2.1 `assets/dod-attestation-template.json`

Template do bloco de auto-attestation que o agente preenche ao final de cada execução.
É o contrato entre o agente e o orchestrator sobre "o que devo atestar".

Contém todos os campos com valores placeholder que o agente deve preencher:
- Bloco `grounding` com docs lidos e missing_required
- Bloco `checklist` com total de regras e regras com fonte válida
- Bloco `coverage` com percentuais e boolean `coverage_matrix_complete`
- Bloco `findings` com booleans `every_finding_*`
- Campos `self_check_passed` e `halt_required`

**DoD:** JSON válido, campos idênticos ao bloco definido em `references/DOD.md`,
comentários inline (`// ...`) explicando o que preencher em cada campo.

---

### 2.2 `assets/second-pass-template.json`

Template do output do Second Pass — a lista de hunks que o agente não reportou com
justificativa. Referenciado no `references/PROTOCOL.md` e necessário para a Fase 3
do pipeline.

Estrutura:
```json
{
  "agent": "security",
  "run_id": "...",
  "hunks_total": 0,
  "hunks_with_finding": 0,
  "hunks_explicitly_cleared": 0,
  "hunks_unaccounted": 0,
  "non_findings": [
    {
      "hunk_id": "src/auth/login.ts:42-58",
      "file": "...",
      "line_start": 0,
      "line_end": 0,
      "reason_not_reported": "..."
    }
  ]
}
```

**DoD:** JSON Schema completo com `required` e `additionalProperties: false` por
objeto, exemplos com razões reais (`"Out of domain: performance concern"`,
`"Confidence 0.65 — uncertain about validated input upstream"`,
`"Already reported as SEC-007 in a previous hunk"`).

---

### 2.3 `assets/non-finding-reasons.md`

Catálogo de razões válidas para `reason_not_reported` no Second Pass. O agente
consulta este arquivo para padronizar as justificativas e evitar que cada execução
invente um vocabulário diferente.

Categorias:
- **Out of domain** — hunk pertence a outro agente
- **Confidence below threshold** — padrão suspeito mas confiança < 0.80
- **Already reported** — mesmo padrão, mesmo arquivo, já virou finding
- **ADR exception** — regra existe mas ADR específico isenta este caso
- **Test file** — código de teste, fora do escopo da regra
- **Generated code** — arquivo gerado por tooling, não editável manualmente
- **Framework handles it** — ORM/framework parametriza automaticamente
- **No DB access in file** — regra de SQL mas arquivo não acessa banco

Cada categoria tem 2-3 frases de exemplo prontas para uso.

**DoD:** pelo menos 8 categorias, cada uma com 2 exemplos de `reason_not_reported`
prontos para copiar.

---

## Entregável 3 — Documentação faltante

**Objetivo:** dois gaps de documentação na skill que causam comportamento ambíguo
durante execução real.

### 3.1 `references/SECOND_PASS.md`

**Por quê existe:** o PROTOCOL.md menciona que o Second Pass acontece, mas não
descreve o protocolo detalhado. O agente não tem onde buscar as instruções quando
chega nessa fase. Os GOTCHAS.md tem uma seção sobre Second Pass, mas é apenas
sobre armadilhas — não o protocolo em si.

**Conteúdo:**
- O que é o Second Pass e por que existe (Pilar 3 — combate preguiça do LLM)
- Como enumerar todos os hunks do diff (por arquivo, por range de linhas)
- Como decidir se um hunk "pertence" a este agente (comparar com `file_patterns`)
- Como classificar cada hunk: `finding` (já foi reportado), `cleared` (justificativa), `unaccounted` (HALT)
- Como preencher o `second-pass-template.json`
- O DoD específico do Second Pass: `hunks_unaccounted == 0`
- 3 exemplos completos: hunk que virou finding, hunk clareado por "out of domain",
  hunk clareado por "confidence abaixo do threshold"

**DoD deste documento:**
- Cobre todos os passos do Second Pass sem referir ao leitor para outro documento
- Inclui exemplos com hunks reais (pode reusar o diff do fixture de teste)
- Define explicitamente o que contar como "hunk": cada bloco `@@` do unified diff
- Menos de 200 linhas (mantém progressive disclosure)

---

### 3.2 Atualização de `references/PROTOCOL.md` — Step 7 e Step 8

**Problema atual:** o PROTOCOL.md Steps 7 e 8 mencionam scripts que agora existem
(`validate_coverage.py`) e scripts que vão existir após o Entregável 1, mas não
descreve quando e como chamar cada um na sequência correta.

**O que adicionar:**

```
Step 7 — Run all validation scripts before declaring done

  Run in this order (stop at first failure):

  1. python scripts/parse_checklist.py <checklist> --output /tmp/rules.json
     Confirms checklist is well-formed. Required before building coverage matrix.

  2. python scripts/validate_coverage.py <run-dir>/agents/security.coverage.json
     Confirms 100% rule × file coverage.

  3. python scripts/check_evidence_literal.py <findings.json> <diff.patch>
     Confirms all evidence_quote values are literal to the diff.

  4. python scripts/check_rule_source.py <findings.json> <grounding-dir>
     Confirms all rule_source values resolve to real grounding sections.

  5. python scripts/validate_dod_attestation.py <run-dir>/agents/security.dod.json
     Final gate: confirms the attestation block is complete and correct.

  All exit 0 → proceed to declare done.
  Any exit 1 → fix the issue, do NOT declare done.
```

**DoD desta atualização:**
- Steps 7 e 8 do PROTOCOL.md cobrem os 5 scripts na ordem correta
- Cada script tem sua invocação exata com os paths corretos do run-dir
- Nenhuma ambiguidade sobre o que fazer quando um script falha

---

## Entregável 4 — Testes isolados da skill

**Objetivo:** os testes E2E existentes testam o pipeline completo. Precisamos de
testes que testam a skill isolada — especificamente os scripts Python — sem precisar
rodar o orchestrator inteiro.

### 4.1 `tests/skills/test_security_skill.py`

**O que testa:**

| Teste | O que valida |
| --- | --- |
| `test_parse_checklist_valid` | 12 regras parseadas do checklist template |
| `test_parse_checklist_missing_source` | Regra sem `source` dispara exit 1 |
| `test_parse_checklist_bad_rule_id` | Formato inválido de rule_id dispara exit 1 |
| `test_check_evidence_literal_passes` | Quote presente no diff → exit 0 |
| `test_check_evidence_literal_fails` | Quote ausente no diff → exit 1 com hint |
| `test_check_evidence_paraphrase_fails` | Quote parafraseado → exit 1 (não é substring) |
| `test_validate_coverage_100pct` | Coverage completa → exit 0 |
| `test_validate_coverage_missing_rule` | Regra ausente da matriz → exit 1 |
| `test_validate_coverage_na_no_reason` | N/A sem justificativa → exit 1 |
| `test_check_rule_source_resolves` | Anchor existe no grounding → exit 0 |
| `test_check_rule_source_missing_anchor` | Anchor inexistente → exit 1 com lista |
| `test_validate_dod_passes` | Attestation completo → exit 0 |
| `test_validate_dod_pct_not_100` | `rules_evaluated_pct: 87` → exit 1 |
| `test_validate_dod_false_positive_field` | `every_evidence_quote_literal: false` → exit 1 |

Total: 14 testes. Todos devem rodar em < 5 segundos sem rede.

**DoD desta suite:**
- 14/14 testes passam
- Nenhum teste depende do orchestrator, do Claude Code, ou do ambiente TRUST instalado
- Cada teste tem fixtures inline (não usa arquivos externos além dos fixtures já existentes)
- Rodam com `python -m pytest tests/skills/test_security_skill.py -v`

---

## Entregável 5 — Integração e revisão final

**Objetivo:** com os 4 entregáveis anteriores prontos, fechar os gaps menores que
ficaram abertos ao longo do desenvolvimento.

### 5.1 Adicionar 3 exemplos ao SKILL.md

O SKILL.md atual tem apenas 1 mini exemplo (SEC-007 — SQLi). Adicionar mais 2 para
cobrir os outros tipos de violação mais comuns:

**Exemplo 2: SEC-001 — Hardcoded secret**
```
Diff: const API_KEY = 'sk-prod-1234567890abcdef';
Rule: SEC-001 — No hardcoded secrets
Finding: confidence 0.99, severity critical, evidence_quote literal
```

**Exemplo 3: SEC-002 — Logging com dado sensível**
```
Diff: console.log(`Login: email=${email}, password=${password}`);
Rule: SEC-002 — No secrets in log statements
Finding: confidence 0.95, severity high
```

**DoD:** cada exemplo tem diff completo, regra do checklist referenciada, finding
JSON completo, e entry da coverage matrix.

---

### 5.2 Verificação cruzada entre artefatos

Antes de fechar, confirmar que todos os artefatos são consistentes entre si:

| Par de artefatos | O que verificar |
| --- | --- |
| `SKILL.md` ↔ `PROTOCOL.md` | Passos no SKILL batem com passos no PROTOCOL |
| `DOD.md` ↔ `dod-attestation-template.json` | Campos idênticos |
| `FINDING_FORMAT.md` ↔ `finding-template.json` | Schema bate com descrição |
| `PROTOCOL.md` ↔ todos os scripts | Toda menção a script tem o arquivo criado |
| `GOTCHAS.md` ↔ `SECOND_PASS.md` | Sem contradição nos edge cases do Second Pass |
| `security.checklist.md` ↔ `parse_checklist.py` | Parser processa todos os 12 rules_id |

**DoD:** checklist preenchido manualmente, sem inconsistências encontradas.

---

### 5.3 `skills/trust-security-review/README.md`

Um README curto (< 60 linhas) dentro da pasta da skill, para que qualquer dev que
abrir a pasta entenda o que cada arquivo faz sem precisar ler tudo.

Conteúdo:
- 1 parágrafo de propósito da skill
- Tabela: artefato | propósito | quando carregar
- Comando para rodar os testes isolados
- Link para `docs/04-skills-spec.md` para entender o padrão agentskills.io

**DoD:** qualquer dev consegue entender a estrutura da skill em < 2 minutos lendo
só este README.

---

## DoD global da skill

A skill `trust-security-review` está "production-ready" quando:

- [ ] **E1** — 4 scripts Python criados, sintaxe válida, exit codes documentados
- [ ] **E1** — `check_evidence_literal.py` detecta paráfrase como falha
- [ ] **E1** — `parse_checklist.py` parseia os 12 rules_id sem erro
- [ ] **E1** — `validate_dod_attestation.py` detecta campos faltantes e percentuais < 100
- [ ] **E1** — `check_rule_source.py` lista anchors disponíveis quando o buscado falha
- [ ] **E2** — `dod-attestation-template.json` tem os mesmos campos do DOD.md
- [ ] **E2** — `second-pass-template.json` tem JSON Schema com required e exemplos
- [ ] **E2** — `non-finding-reasons.md` tem 8+ categorias com 2 exemplos cada
- [ ] **E3** — `SECOND_PASS.md` cobre o protocolo completo em < 200 linhas
- [ ] **E3** — PROTOCOL.md Steps 7-8 referenciam os 5 scripts na ordem correta
- [ ] **E4** — 14/14 testes de skill passam em < 5s sem dependências externas
- [ ] **E5** — SKILL.md tem 3 exemplos (SQLi, secret, logging)
- [ ] **E5** — Verificação cruzada sem inconsistências
- [ ] **E5** — `README.md` da skill descreve todos os artefatos em < 60 linhas
- [ ] **Spec** — `skills-ref validate` passa (ou equivalente manual 10/10)
- [ ] **Spec** — SKILL.md < 500 linhas após adição dos exemplos

---

## Ordem de execução recomendada

```
E1.1 check_evidence_literal.py        ← desbloqueia E4 (tests)
E1.2 parse_checklist.py               ← desbloqueia E4 (tests)
E1.3 validate_dod_attestation.py      ← depende de E2.1
E2.1 dod-attestation-template.json    ← execute antes de E1.3
E1.4 check_rule_source.py             ← independente
E2.2 second-pass-template.json        ← independente
E2.3 non-finding-reasons.md           ← independente
E3.1 SECOND_PASS.md                   ← independente
E3.2 Atualização PROTOCOL.md          ← execute após todos E1
E4.1 tests/skills/test_security_skill.py ← execute por último
E5.1 Exemplos no SKILL.md             ← independente
E5.2 Verificação cruzada              ← execute depois de todos
E5.3 README.md da skill               ← execute depois de todos
```

Estimativa: **1 sessão de trabalho focada** (3-4h) para implementar tudo.
Os entregáveis são independentes o suficiente para paralelizar E1, E2, E3.

---

## O que NÃO está no escopo deste plano

Para evitar scope creep, as seguintes coisas ficam **fora** deste plano e vão
para as skills restantes (v1.0):

- Outros 5 agentes (contracts, data, performance, conventions, tests)
- `trust-second-pass` como skill separada do orquestrador
- `trust-meta-review` como skill separada
- Integração com Notion/HTTP (v1.1)
- Testes de integração com Claude Code real

---

*Plano gerado em: 2026-05-18*
*Skill atual: v1.0.0 (MVP estrutural)*
*Skill após este plano: v1.1.0 (production-ready)*
