---
description: Valida o setup do TRUST, fontes de grounding e integrações — execute após instalar ou quando algo parecer quebrado
---

# /trust doctor

Validates the TRUST setup and all grounding sources. Run after install, after cloning the setup repo, or whenever something seems broken.

## Usage

```
/trust doctor [--fix]
```

**Flags:**
- `--fix` — attempt to auto-fix simple issues (missing `.env.local`, outdated config)

## What it checks

Four areas: environment variables, grounding sources, targets, and skills.
Exits with code 1 if any errors are found.

## When to load

| File | When to load |
| --- | --- |
| `commands/references/doctor-checks.md` | Always — contains all check definitions and output format |
| `commands/references/doctor-fix.md` | Only when `--fix` flag is passed |
