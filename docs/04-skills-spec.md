# Skills Spec — TRUST

> **Pergunta que este doc responde:** como as skills do TRUST seguem o padrão oficial **[agentskills.io](https://agentskills.io/specification)**, e por quê isso importa.

---

## 1. Por que seguir o padrão agentskills.io

O Agent Skills é o **padrão aberto** para dar capacidades a agentes de IA. Ele foi originado pela Anthropic e adotado por múltiplos clientes (não só Claude Code). Seguir esse padrão dá ao TRUST três vantagens reais:

1. **Portabilidade** — qualquer cliente compatível com agentskills consegue rodar nossas skills
2. **Progressive disclosure** — o motor carrega só o necessário, não infla o contexto
3. **Validação automatizada** — existe um validador oficial (`skills-ref validate`)

Toda skill do TRUST adota a spec **rigorosamente**.

---

## 2. Anatomia de uma skill do TRUST

Cada skill vive em sua própria pasta dentro de `skills/`:

```
skills/trust-security-review/
├── SKILL.md                      # OBRIGATÓRIO — frontmatter + instruções
├── references/                   # OPCIONAL — material de apoio sob demanda
│   ├── PROTOCOL.md
│   ├── FINDING_FORMAT.md
│   ├── DOD.md
│   └── GOTCHAS.md
├── scripts/                      # OPCIONAL — código executável
│   ├── validate_coverage.py
│   └── check_evidence_literal.py
└── assets/                       # OPCIONAL — templates, schemas
    ├── finding-template.json
    └── coverage-template.json
```

---

## 3. Frontmatter YAML obrigatório

A spec exige YAML frontmatter no topo de cada `SKILL.md`. Exemplo do `trust-security-review`:

```yaml
---
name: trust-security-review
description: Reviews pull request diffs for security violations defined in the project's security checklist and grounding documents. Use when a developer requests TRUST security review, or when analyzing code changes against project-specific security rules like SQL injection, secret handling, AuthN/AuthZ, and input validation policies.
license: MIT
compatibility: Designed for Claude Code. Requires TRUST_SETUP_PATH env var and Python 3.11+.
metadata:
  framework: TRUST
  agent_id: security
  agent_version: "1.0.0"
  pilar: "1-especializacao,2-grounding,3-second-pass,7-meta-review"
---
```

### Regras dos campos

| Campo | Regra | Por quê |
| --- | --- | --- |
| `name` | minúsculo, hífens, 1-64 chars, match com nome da pasta | Identificador único |
| `description` | até 1024 chars, descreve **o quê** e **quando** usar | Usada na discovery (progressive disclosure) |
| `license` | string curta | Recomendado para skills distribuídas |
| `compatibility` | até 500 chars | Indica dependências de ambiente |
| `metadata` | mapa key-value livre | Onde colocamos info específica do TRUST |

### Por que naming `trust-<dominio>-<acao>`

Todas as skills do TRUST seguem o padrão:

- `trust-security-review`
- `trust-contracts-review`
- `trust-second-pass`
- `trust-meta-review`

O prefixo `trust-` evita colisão com skills de outros frameworks, e a estrutura `<dominio>-<acao>` deixa o propósito explícito.

---

## 4. Progressive Disclosure no TRUST

A spec recomenda **`SKILL.md` < 500 linhas e < 5000 tokens**. O TRUST adota isso à risca movendo conteúdo para `references/`:

| Conteúdo | Onde fica | Quando o agente carrega |
| --- | --- | --- |
| Identidade, escopo, regras-mestras | `SKILL.md` (raiz) | Sempre, ao ativar a skill |
| Protocolo de execução detalhado | `references/PROTOCOL.md` | Quando vai executar |
| Formato canônico de finding | `references/FINDING_FORMAT.md` | Antes de gerar findings |
| Critérios de Definition of Done | `references/DOD.md` | Antes da self-attestation |
| Anti-padrões e edge cases | `references/GOTCHAS.md` | Quando o agente encontrar situação ambígua |

O `SKILL.md` raiz **diz explicitamente quando carregar cada reference**:

```markdown
## Protocolo de execução

1. Leia `references/PROTOCOL.md` para o passo a passo completo
2. Antes de emitir findings, leia `references/FINDING_FORMAT.md`
3. Se encontrar uma situação ambígua, consulte `references/GOTCHAS.md`
4. Antes de declarar done, leia `references/DOD.md` e preencha a attestation
```

Isso é o que a spec chama de **"telling the agent when to load each file"**.

---

## 5. Scripts em Python

Como decidimos Python como linguagem dos scripts (aderência à spec):

```python
# scripts/validate_coverage.py

"""Valida que o coverage.json de um agente tem 100% das regras avaliadas.

Usage:
    python validate_coverage.py <path-to-coverage.json>

Exit codes:
    0  → cobertura completa
    1  → cobertura incompleta (HALT)
    2  → erro de leitura do arquivo
"""

import json
import sys
from pathlib import Path


def validate_coverage(coverage_path: Path) -> tuple[bool, str]:
    """Returns (ok, message)."""
    try:
        data = json.loads(coverage_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return False, f"Cannot read coverage file: {e}"

    total_rules = data.get("rules_in_checklist_total", 0)
    evaluated = data.get("rules_evaluated_total", 0)

    if total_rules == 0:
        return False, "No rules declared in coverage — invalid file"

    if evaluated < total_rules:
        missing = total_rules - evaluated
        return False, f"Coverage incomplete: {evaluated}/{total_rules} rules ({missing} missing)"

    return True, f"Coverage complete: {evaluated}/{total_rules} rules"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: validate_coverage.py <coverage.json>", file=sys.stderr)
        sys.exit(2)

    ok, msg = validate_coverage(Path(sys.argv[1]))
    print(msg)
    sys.exit(0 if ok else 1)
```

Características dos scripts do TRUST:

- **Self-contained** — cada script é independente, sem importar de outros scripts da skill
- **Exit codes claros** — agentes leem o exit code para decidir HALT
- **Sem dependências externas pesadas** — usar só stdlib quando possível
- **Type hints** — clareza para LLMs lerem

---

## 6. Assets — templates JSON

A pasta `assets/` carrega templates concretos que o agente preenche:

```json
// assets/finding-template.json

{
  "agent": "<AGENT_ID>",
  "rule_id": "<RULE_ID>",
  "rule_source": "<PATH#section>",
  "file": "<file-from-diff>",
  "line_start": 0,
  "line_end": 0,
  "severity": "critical|high|medium|low",
  "confidence": 0.0,
  "claim": "<one-sentence description>",
  "evidence_quote": "<LITERAL code, copy-paste>",
  "why_it_matters": "<concrete consequence in THIS project context>",
  "suggestion": "<proposed fix>",
  "false_positive_risk": "low|medium|high",
  "false_positive_reason": "<null if low; explain if medium/high>"
}
```

Templates evitam que cada agente reinvente o formato. Eles ficam em `assets/` porque carregam **on-demand** — só quando o agente vai produzir um finding.

---

## 7. Validação

Use a ferramenta oficial:

```bash
# instalar
pip install skills-ref

# validar uma skill
skills-ref validate skills/trust-security-review/

# validar todas
for skill in skills/*/; do
    skills-ref validate "$skill"
done
```

O CI do framework roda essa validação em todo PR.

---

## 8. Checklist de uma nova skill TRUST

Quando criar uma skill nova:

- [ ] Pasta com nome no formato `trust-<dominio>-<acao>`
- [ ] `SKILL.md` com YAML frontmatter completo
- [ ] `name` igual ao nome da pasta
- [ ] `description` clara, com palavras-chave de ativação
- [ ] `metadata.framework: TRUST`
- [ ] `metadata.agent_id` único
- [ ] Body do `SKILL.md` < 500 linhas
- [ ] References/ com PROTOCOL, FINDING_FORMAT, DOD, GOTCHAS quando aplicável
- [ ] Scripts/ com utilitários necessários (Python, type hints, exit codes)
- [ ] Assets/ com templates JSON
- [ ] `skills-ref validate` passa
- [ ] Doc atualizado em `docs/04-skills-spec.md` (se introduzir novo padrão)

---

## 9. Lista de skills do framework

| Skill | Pilar(es) | Função |
| --- | --- | --- |
| `trust-security-review` | 1, 2 | Agente especialista em segurança |
| `trust-contracts-review` | 1, 2 | Agente especialista em contratos de API |
| `trust-data-review` | 1, 2 | Agente especialista em banco/migrations |
| `trust-performance-review` | 1, 2 | Agente especialista em performance |
| `trust-conventions-review` | 1, 2 | Agente especialista em convenções de código |
| `trust-tests-review` | 1, 2 | Agente especialista em qualidade de testes |
| `trust-second-pass` | 3 | Força re-leitura honesta de cada agente |
| `trust-precision-gate` | 4 | Filtra findings por confiança |
| `trust-meta-review` | 7 | Anti-hallucination |

---

**Próximo:** [docs/05-glossario.md](05-glossario.md) — vocabulário do TRUST.
