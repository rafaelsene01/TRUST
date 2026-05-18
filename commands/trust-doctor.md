# /trust doctor

Validates the TRUST setup and all grounding sources. Run this after install,
after cloning the setup repo, or whenever something seems broken.

## Usage

```
/trust doctor [--fix]
```

**Flags:**
- `--fix` — attempt to auto-fix simple issues (missing `.env.local`, outdated config)

---

## Checks performed

### 1. Environment

| Check | Pass | Fail |
| --- | --- | --- |
| `TRUST_SETUP_PATH` is set | ✅ | ❌ — shows how to set it |
| `TRUST_SETUP_PATH` exists on disk | ✅ | ❌ — shows `git clone` command |
| `trust.config.yaml` present and valid YAML | ✅ | ❌ — shows the parse error |
| Python 3.11+ available | ✅ | ⚠️  warning |
| `git` available | ✅ | ❌ |

### 2. Grounding sources

For each source declared in `trust.config.yaml`:

| Check | Pass | Fail |
| --- | --- | --- |
| Adapter is supported (`filesystem` in MVP) | ✅ | ❌ |
| Base path resolves to an existing directory | ✅ | ❌ offers to configure |
| Required docs exist in source | ✅ | ❌ lists missing docs |
| No required doc is empty (< 200 bytes) | ✅ | ⚠️  lists stub files |

### 3. Targets

For each `targets/*.yaml`:

| Check | Pass | Fail |
| --- | --- | --- |
| File is valid YAML | ✅ | ❌ |
| `remote_url` field is present | ✅ | ⚠️  warning |
| `repo_path` resolves on this machine | ✅ | ⚠️  prompts to configure |
| Enabled agents have their SKILL.md | ✅ | ❌ |
| Checklist files referenced by agents exist | ✅ | ❌ |

### 4. Skills

For each skill referenced in config:

| Check | Pass | Fail |
| --- | --- | --- |
| SKILL.md exists | ✅ | ❌ — re-install framework |
| SKILL.md has YAML frontmatter | ✅ | ❌ |
| References listed in SKILL.md exist | ✅ | ⚠️  |

---

## Execution

Print results in this format:

```
🩺 TRUST doctor — health check

Environment
  ✅ TRUST_SETUP_PATH = ~/work/payments-team-trust
  ✅ trust.config.yaml valid
  ✅ Python 3.11 found
  ✅ git found

Grounding sources
  ✅ in-setup (filesystem) — ./grounding/
     7 required docs present (47KB total)
  ⚠️  second-brain (filesystem) — TRUST_SECONDBRAIN_PATH not set
     → To configure: add TRUST_SECONDBRAIN_PATH=<path> to .env.local
     → Or disable: set optional: true in config (already set)

Targets
  ✅ api-payments — repo path found, 6 agents configured
  ⚠️  payments-frontend — repo_path not found on this machine
     ~/work/payments-frontend does not exist
     → Clone it or update repo_path in targets/payments-frontend.yaml

Skills
  ✅ trust-security-review — SKILL.md valid, 4 references present

─────────────────────────────
Status: 1 warning, 0 errors

No errors found — you can run /trust review-pr
```

If errors are found, exit with code 1 and print:
```
─────────────────────────────
Status: 0 warnings, 2 errors

Fix errors above before running /trust review-pr
```

---

## --fix mode

When `--fix` is passed, for each fixable issue:
- Missing `TRUST_SETUP_PATH` → print export command and offer to add to shell rc
- Missing `repo_path` → prompt for path and update `.env.local`
- Stub grounding doc → offer to run `/trust map codebase` to populate

Non-fixable issues (missing skills, invalid YAML, broken git) are always manual.
