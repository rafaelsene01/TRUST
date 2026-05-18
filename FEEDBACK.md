# TRUST — Feedback do Piloto

> Registro de feedback dos devs que usaram o TRUST em PRs reais.
> Usado pelo `/trust learn from-history` para calibrar thresholds e sugerir novas regras.

---

## Como registrar feedback

Após cada PR revisado pelo TRUST, adicione uma entrada neste arquivo:

```markdown
### PR: <url-do-pr> · Data: YYYY-MM-DD · Dev: <nome>

**Findings úteis:** X de Y (ex: 3 de 5)
**Falsos positivos:** <descreva os findings que não faziam sentido>
**Falsos negativos:** <bugs que o TRUST não pegou mas deveria>
**NPS (1-10):** X
**Comentário livre:** ...
```

---

## Entradas

*(nenhuma ainda — aguardando piloto real)*

---

## Métricas agregadas

| Métrica | Meta v1.0 | Atual |
| --- | --- | --- |
| Adoção — % PRs com review TRUST | > 80% | — |
| False positive rate | < 20% | — |
| Hallucinations por 100 findings | < 1 | — |
| HALT rate | < 5% | — |
| NPS dos devs (1-10) | ≥ 7 | — |
| Time-to-review (PR 50 arquivos) | < 5 min | — |
