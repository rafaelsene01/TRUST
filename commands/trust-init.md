---
description: Onboarding interativo para criar o repo de setup do TRUST para o seu time — gera config, templates de grounding e valida o setup
---

# /trust init

Interactive onboarding to create a TRUST setup repo for your team.

## Usage

```
/trust init [pilot|team|solo|enterprise]
```

If no profile is specified, walk through a wizard to choose.

## Profiles

| Profile | Where config lives | Best for |
| --- | --- | --- |
| `pilot` | Separate setup repo | First deployment, zero product-repo footprint |
| `team` | Inside product repo under `.trust/` | Team that wants config versioned with code |
| `solo` | `~/.trust-solo/` | Individual developer, second brain as grounding |
| `enterprise` | Hierarchical corp/team/personal layers | Multi-team org with governance requirements |

## When to load

| File | When to load |
| --- | --- |
| `commands/references/init-pilot.md` | Profile is `pilot` or not yet chosen |
| `commands/references/init-team.md` | Profile is `team` |
| `commands/references/init-solo.md` | Profile is `solo` |
| `commands/references/init-enterprise.md` | Profile is `enterprise` |
