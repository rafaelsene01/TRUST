# Onboarding — TRUST

> **Pergunta que este doc responde:** como saio do zero até o primeiro review rodando no meu projeto.
>
> **Versão:** MVP `v0.1.0` — Profile Pilot, Adapter Filesystem, Agente Security.
> Features marcadas com ⏳ estão em desenvolvimento (veja [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md)).

---

## 1. Pré-requisitos

| Item | Versão mínima | Por quê |
| --- | --- | --- |
| **Claude Code** | versão atual | Roda os agentes localmente |
| **Python** | 3.11+ | Os scripts das skills são Python |
| **git** | 2.30+ | Captura do diff e detecção de remote |
| **gh** ou **glab** | opcional | Para postar comentários em PRs |

---

## 2. Instalação (uma vez por máquina)

### Opção A — via plugin manager (recomendado)

```bash
/plugin add github.com/seu-user/trust
```

### Opção B — via install script

```bash
curl -fsSL https://raw.githubusercontent.com/seu-user/trust/main/install.sh | bash
```

O script:
1. Clona o repo do framework para `~/.trust/`
2. Adiciona o diretório de skills ao Claude Code (`~/.claude/skills/`)
3. Adiciona os slash commands (`~/.claude/commands/`)
4. Cria o config global do usuário em `~/.trust/user.config.yaml`

Verifique:

```bash
/trust --version
# TRUST v1.0.0
```

---

## 3. Criando o setup do time (uma vez por time)

Este passo é feito por **um membro do time**. Os outros apenas clonam.

### Passo 3.1 — Criar repo no GitHub/GitLab

Crie um repo vazio chamado `<nome-do-time>-trust` (ex: `payments-team-trust`).

### Passo 3.2 — Executar `/trust init pilot`

Em qualquer pasta, rode:

```bash
/trust init pilot
```

O framework abre um onboarding interativo:

```
╭─ TRUST — Pilot Mode ────────────────────────────────────╮
│  Para times piloto numa empresa onde ainda não há       │
│  standards corporativos. Setup desacoplado do produto.  │
╰─────────────────────────────────────────────────────────╯

📁 Onde criar o setup repo localmente?
> ~/work/payments-team-trust

🏷️  Nome do time:
> Payments Squad

🎯 Quais repos do produto este setup vai revisar?
   (você pode adicionar mais depois com /trust target add)

Repo 1:
> ~/work/api-payments
   ✓ Detectei: TypeScript + NestJS + PostgreSQL
   ✓ git remote: git@github.com:empresa/api-payments.git

Adicionar outro? [s/n]
> n

📚 Sources de grounding:
   Camada TIME (in-setup) — sempre ativa
   ✓ Adicionada: payments-team-trust/grounding/

   Camada PESSOAL (second brain) — opcional
   [1] Adicionar Obsidian/Notion
   [2] Pular
> 2

🧩 Quer fazer o map do repo-alvo agora? ⏳ (disponível em v1.0)
> n

✅ Setup criado em ~/work/payments-team-trust/
✅ Targets registrados: 1 repo

📋 Próximos passos:
   cd ~/work/payments-team-trust
   git init && git remote add origin <url-do-repo-do-time>

   # criar os docs de grounding manualmente (ou copiar os templates)
   cp ~/.trust/templates/grounding/06-security-policy.md grounding/

   # primeiro review
   cd ~/work/api-payments
   export TRUST_SETUP_PATH=~/work/payments-team-trust
   /trust review-pr
```

### Passo 3.3 — Criar os docs de grounding

No MVP, os grounding docs são criados manualmente a partir dos templates incluídos no framework.
Copie e adapte para o contexto do seu time:

```bash
cd ~/work/payments-team-trust
mkdir -p grounding

# Copiar templates (adapte os valores entre {{ }})
cp ~/.trust/templates/grounding/06-security-policy.md grounding/
cp ~/.trust/templates/checklists/security.checklist.md checklists/

# Criar docs de arquitetura manualmente (ver fixtures de exemplo em tests/fixtures/mock-grounding/)
```

O agente `security` precisa ao menos de `grounding/06-security-policy.md` e
`checklists/security.checklist.md` para rodar sem HALT.

> ⏳ **v1.0:** `/trust map codebase` e `/trust approve-drafts` vão automatizar
> a geração desses docs a partir do código existente.

### Passo 3.4 — Commitar e fazer push

```bash
git add .
git commit -m "feat: bootstrap TRUST setup para Payments Squad"
git remote add origin git@github.com:empresa/payments-team-trust.git
git push -u origin main
```

---

## 4. Onboarding dos outros devs do time

Cada outro dev do time só precisa de **dois comandos**:

```bash
# Clone do setup do time
git clone git@github.com:empresa/payments-team-trust.git ~/work/payments-team-trust

# Adicionar a env var ao shell (zshrc/bashrc)
echo 'export TRUST_SETUP_PATH=~/work/payments-team-trust' >> ~/.zshrc
source ~/.zshrc
```

Verifique:

```bash
/trust doctor
```

Se tudo estiver verde, o dev já pode rodar reviews.

---

## 5. Primeiro review

Dentro do repo do produto:

```bash
cd ~/work/api-payments
git checkout -b feat/PAY-123
# ... fazer mudanças no código ...
git add . && git commit -m "feat: add payment retry logic"

# rodar o review TRUST
/trust review-pr feat/PAY-123
```

O framework:

1. **Auto-descobre o target** — casa o `git remote get-url origin` com algum `target.yaml` do setup
2. **Executa as 8 fases** com DoD estrito (veja fluxo em [docs/02-arquitetura.md](02-arquitetura.md#2-as-8-fases-de-execução))
3. **Gera o REVIEW.md** em `${TRUST_REVIEW_OUTPUT}/api-payments/feat-PAY-123/REVIEW.md`
4. **Opcionalmente comenta no PR** se `comment_on_pr: true` no target

Output esperado em caso de sucesso:

```
🚀 TRUST run iniciado — run-id: 2026-05-17-1430-feat-PAY-123
   target: api-payments
   diff: 12 arquivos, 47 hunks

⏳ Fase 1/7 — Grounding...           ✅ 7 docs carregados (47KB)
⏳ Fase 2/7 — Agentes especialistas... ✅ 6 agentes, 89 regras avaliadas
⏳ Fase 3/7 — Second Pass...         ✅ 47/47 hunks com veredito
⏳ Fase 4/7 — Precision Gate...      ✅ 4 findings, 2 silenced
⏳ Fase 5/7 — Meta-Review...         ✅ 4/4 validados, 0 hallucinations
⏳ Fase 6/7 — Rastreabilidade...     ⏭️  skipped (não configurado)
⏳ Fase 7/7 — Output...              ✅ REVIEW.md gerado

📋 REVIEW disponível em:
   ~/Documents/trust-reviews/api-payments/feat-PAY-123/REVIEW.md

   findings: 4 (1 critical, 2 high, 1 medium)
   silenced: 2 (low confidence)
   hallucinations interceptadas: 0
```

Em caso de HALT:

```
⏳ Fase 2/7 — Agentes especialistas...
❌ HALT na Fase 2
   Agente: security
   Motivo: coverage_matrix incomplete — 3/5 regras com veredito (esperado: 100%)

   Artefatos preservados em:
   ~/work/payments-team-trust/runs/2026-05-17-1430-feat-PAY-123/

   Próximos passos:
   1. Inspecione: cat runs/.../agents/security.coverage.json
   2. Corrija o problema (skill incompleta, checklist faltando regra, etc)
   3. /trust cleanup 2026-05-17-1430-feat-PAY-123  # quando resolvido
   4. /trust review-pr feat/PAY-123                # tente novamente
```

---

## 6. Manutenção contínua

### `/trust doctor` — health check completo

Roda regularmente, especialmente depois de:

- Atualizar o framework (`/plugin update trust`)
- Mudar o setup do time (`git pull` no setup repo)
- Trocar de máquina

O doctor valida:

- ✓ Env var `TRUST_SETUP_PATH` definida
- ✓ Setup repo acessível
- ✓ Sources de grounding alcançáveis (health_check em cada adapter)
- ✓ Todos os targets têm `repo_path` válido
- ✓ Skills do framework presentes
- ✓ Tokens (se houver) válidos

### `/trust map codebase` — bootstrap em repos novos ⏳ v1.0

Quando adicionar um novo repo-alvo ao setup, o bootstrap manual por ora é:

```bash
cd ~/work/payments-team-trust
# Criar manualmente o target.yaml para o novo repo (veja templates/target.yaml.template)
# Criar/adaptar os grounding docs específicos desse repo
```

> ⏳ **v1.0:** `/trust target add` e `/trust map codebase` automatizarão este passo.

### `/trust cleanup <run-id>` — limpar runs antigas

Roda quando houve HALT e você já corrigiu o problema:

```bash
/trust cleanup 2026-05-17-1430-feat-PAY-123
# remove a pasta de run e o marker .trust-halt
```

---

## 7. Troubleshooting

| Sintoma | Causa provável | Como resolver |
| --- | --- | --- |
| `TRUST_SETUP_PATH not set` | env var não exportada | `export TRUST_SETUP_PATH=...` no shell |
| `no target matches current repo` | git remote não bate com nenhum `target.yaml` | Verificar `remote_url` nos targets |
| `HALT: grounding doc missing` | doc obrigatório não existe | `ls grounding/` e completar |
| `HALT: coverage incomplete` | agente não conseguiu avaliar todas as regras | Inspecionar `<dominio>.coverage.json` |
| `HALT: unaccounted hunks` | Second Pass encontrou diff não revisado | Inspecionar `<dominio>.second-pass.json` |
| `notion adapter: 401` | token Notion inválido/expirado | Atualizar `NOTION_TOKEN` em `.env.local` |

---

**Próximo:** [docs/04-skills-spec.md](04-skills-spec.md) — como cada skill segue a spec oficial do agentskills.io.
