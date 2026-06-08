---
description: Executa um review completo do TRUST sem o agente de testes — igual ao trust-review-pr, mas ignora cobertura de testes (útil para PRs sem testes intencionalmente)
---

# /trust review-pr-no-test

Executa o review completo do TRUST em um branch de feature, pulando o agente `trust-tests-review`.

Use este comando quando o PR não inclui testes por decisão explícita — ex.: mudanças de configuração, scripts de migração, documentação ou funcionalidades onde testes serão adicionados separadamente.

## Uso

```
/trust review-pr-no-test [<feature-branch>] [--base <base-branch>]
```

**Argumentos:**
- `feature-branch` — branch a revisar. Padrão: branch atual.
- `--base` — branch base para o diff. Padrão: `main`.

**Exemplos:**
```
/trust review-pr-no-test feat/152
/trust review-pr-no-test feat/152 --base develop
/trust review-pr-no-test
```

## O que este comando faz

Executa o pipeline TRUST de 8 fases com **6 agentes** (segurança, contratos, convenções, performance, dados, meta-review), **pulando o agente de testes**.

Antes de iniciar o Step 4 do protocolo, remova `tests` de `agent_context["agents_to_run"]` e registre no log:

```
⚠️  Agente de testes desativado (trust-review-pr-no-test)
```

O REVIEW.md gerado inclui a nota:
```
> **Escopo:** review sem agente de testes — cobertura de testes não foi avaliada nesta execução.
```

## Quando carregar

| Arquivo | Quando carregar |
| --- | --- |
| `commands/references/review-pr-protocol.md` | Antes de executar — contém o protocolo completo passo a passo |
