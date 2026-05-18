# Changelog — TRUST

All notable changes to this project will be documented here.

Format: [Semantic Versioning](https://semver.org/)

---

## [1.2.0] — 2026-05-18

### v1.2 — Rastreabilidade

Phase 6 is now fully operational. Every finding in `REVIEW.md` can be linked
back to the Jira ticket (or local spec file) that originated the change.

**New core modules:**
- `core/spec_parser.py` — Parses `.spec.md` files with YAML frontmatter
  - Extracts `ticket_id`, `title`, `components`, `labels`, `acceptance_criteria`
  - `find_spec_for_ticket(spec_dir, ticket_id)` — canonical filename + frontmatter scan
  - Stdlib only (no PyYAML dependency); handles quoted values and inline lists
- `core/traceability.py` — Orchestrates Phase 6 end-to-end
  - Branch → ticket ID (via `branch_pattern` or default fallback)
  - Resolution order: local spec file → Jira API → `not_found` stub
  - Never raises: all errors captured in `TraceabilityResult.warning`
  - Annotates every finding with a `traced_to` block

**`core/jira_integration.py` (already in v1.2 scope):**
- `JiraClient.get_ticket()` → `JiraTicket | JiraError`
- ADF-to-text conversion for Jira Cloud descriptions
- Branch-pattern extraction with `{ticket}` placeholder and fallback regex

**Orchestrator updates (`core/orchestrator.py`):**
- `_run_phase_6_traceability()` — real Phase 6 (replaces skip-only stub)
- `_run_phase_7_output()` now accepts `traceability_report` and renders a
  ticket header block (title, status, components, AC) in `REVIEW.md`
- `run_review()` routes to real Phase 6 when `traceability.enabled: true`

**New slash command:**
- `commands/trust-trace.md` — `/trust trace check [<branch>]` and
  `/trust trace show [<branch>]`

**New template:**
- `templates/spec.md.template` — canonical spec file layout with frontmatter

**Tests:**
- `tests/e2e/test_v1_2.py` — 40 tests covering all new components (100% offline)

---

## [1.1.0] — 2026-05-18

### v1.1 — Sources & UX

External grounding sources (Notion, HTTP/Confluence), disk cache with TTL,
progress reporter, run history command, and actionable error messages.

**New adapters:**
- `adapters/notion_adapter.py` — Reads Notion pages and databases via API v1
  - Converts Notion blocks to Markdown (paragraph, headings, code, lists, tables, …)
  - Handles pagination (up to 500 blocks per page)
  - Extracts page IDs from bare IDs, `page:<id>`, `db:<id>`, or full Notion URLs
- `adapters/http_adapter.py` — Reads HTTP/HTTPS endpoints with auth
  - Supports `bearer`, `basic`, and custom header auth (all via env vars)
  - Normalises `text/html` → plain text, `application/json` → Markdown
  - All errors include `Next action:` hints

**New core modules:**
- `core/source_cache.py` — Disk-backed TTL cache for external sources
  - Default TTL: 60 min, configurable per source with `cache_ttl_minutes`
  - Keyed by `(source_id, doc_path)` hash, stored under `.trust-cache/`
  - Methods: `get`, `put`, `invalidate`, `clear_source`, `stats`
- `core/progress_reporter.py` — Terminal progress bar for pipeline phases
  - Phase context manager with `step()` and `message()` calls
  - ANSI bar on supporting terminals; plain text fallback for CI
  - Phases faster than 1s suppressed by default (no flicker)
  - `summary()` prints per-phase timing table

**grounding_loader.py updates:**
- Added `notion` and `http` adapter dispatch in `load_grounding()`
- `validate_grounding_dod()` accepts `previous_sha_map` to detect changes
- Volatile sources: hash change emits info, never triggers errors
- Non-volatile sources: hash change emits warning, never triggers errors

**New slash command:**
- `commands/trust-runs.md` — `/trust runs list/show/clean`

**Documentation:**
- `docs/02-arquitetura.md` — New sections on external adapters, cache, and UX
- `docs/03-onboarding.md` — Updated to v1.1; added Notion/Confluence setup guide

**Tests:**
- `tests/e2e/test_v1_1.py` — 28 tests covering all new components (100% offline)

---

## [1.0.0] — 2026-05-17

### v1.0 — Pilot Ready

All 6 specialist agents, Second Pass, and Meta-Review are now implemented.

**5 new specialist skills:**
- `skills/trust-contracts-review/` — API contract violations (8 rules: CON-001..CON-008)
- `skills/trust-data-review/` — Database migrations and schema changes (8 rules: DAT-001..DAT-008)
- `skills/trust-performance-review/` — N+1, unbounded queries, missing timeouts (6 rules: PERF-001..PERF-006)
- `skills/trust-conventions-review/` — Naming, logging, error handling conventions (6 rules: CONV-001..CONV-006)
- `skills/trust-tests-review/` — Test quality, coverage, mock usage (6 rules: TEST-001..TEST-006)

**2 new pipeline skills:**
- `skills/trust-second-pass/` — Phase 3: aggregate hunk accounting across all agents
- `skills/trust-meta-review/` — Phase 5: anti-hallucination validation (5 checks per finding)

**5 new checklist templates (`templates/checklists/`):**
- `contracts.checklist.md`, `data.checklist.md`, `performance.checklist.md`
- `conventions.checklist.md`, `tests.checklist.md`

**Each skill includes:**
- `SKILL.md` with agentskills.io-compliant frontmatter and domain-specific example
- `references/PROTOCOL.md` — step-by-step execution protocol
- `references/DOD.md` — definition of done and self-attestation block
- `references/GOTCHAS.md` — domain-specific edge cases
- `references/FINDING_FORMAT.md` — field-by-field rules for findings
- `scripts/validate_coverage.py` — coverage validation script
- `assets/finding-template.json` and `assets/coverage-template.json`

**Status:** 5 agent skills are structural (SKILL.md + references + scripts).
Second Pass and Meta-Review have full PROTOCOL.md execution protocols.
Validation scripts for contracts/data/performance/conventions/tests (equivalent
to security's check_evidence_literal, parse_checklist, etc.) are v1.1 scope.

---

## [0.1.1] — 2026-05-17

### trust-security-review: production-ready (skill v1.1.0)

Fechamento da skill `trust-security-review` com todos os artefatos de validação
mecânica, documentação de Second Pass, e suite de testes isolados.

**Scripts adicionados (`skills/trust-security-review/scripts/`):**
- `check_evidence_literal.py` — confirma que `evidence_quote` é literal (byte a byte) no diff
- `parse_checklist.py` — parseia `security.checklist.md` em JSON estruturado e determinístico
- `validate_dod_attestation.py` — gate final de validação do bloco de auto-attestation
- `check_rule_source.py` — verifica que cada `rule_source` resolve para uma seção real do grounding

**Assets adicionados (`skills/trust-security-review/assets/`):**
- `dod-attestation-template.json` — JSON Schema completo do bloco DoD
- `second-pass-template.json` — JSON Schema do relatório de Second Pass
- `non-finding-reasons.md` — catálogo de 8 categorias de justificativa para hunks não reportados

**Documentação adicionada (`skills/trust-security-review/references/`):**
- `SECOND_PASS.md` — protocolo completo do Second Pass (5 passos + 3 exemplos)

**Documentação atualizada:**
- `references/PROTOCOL.md` — Steps 7-8 reescritos com os 5 scripts na ordem correta
- `SKILL.md` — 3 exemplos completos (SEC-007 SQLi, SEC-001 hardcoded secret, SEC-002 log de senha)
- `README.md` da skill — tabela de todos os artefatos com propósito e quando carregar

**Testes:**
- `tests/skills/test_security_skill.py` — 14/14 testes isolados, < 0.1s, sem dependências externas

---

## [0.1.0-mvp] — 2026-05-18

### First release — MVP (Vertical Slice)

**What works end-to-end:**
- Phase 0: Trigger — diff capture via `git diff`, run-id generation
- Phase 1: Grounding — filesystem adapter, 7+ doc loading, sha256 manifest, DoD validation
- Phase 2: Agent execution — `trust-security-review` skill (SKILL.md + references + scripts + assets)
- Phase 4: Precision Gate — confidence threshold filtering (default 0.80)
- Phase 5: Meta-review — evidence_quote literal validation against diff
- Phase 6: Traceability — skip with explicit flag when disabled
- Phase 7: Output — REVIEW.md with findings grouped by severity, silenced appendix, hallucinations appendix

**Core modules shipped:**
- `core/models.py` — shared dataclasses
- `core/config_loader.py` — YAML config parsing with env var substitution
- `core/grounding_loader.py` — filesystem doc loading with DoD validation
- `core/halt_handler.py` — HALT sequence (record + marker + message + raise)
- `core/run_manifest.py` — run lifecycle management
- `core/orchestrator.py` — 8-phase pipeline driver

**Adapters:**
- `adapters/filesystem_adapter.py` — reads from local disk (files, directories, globs)

**Skills:**
- `skills/trust-security-review/` — full agentskills.io spec-compliant skill
  - SKILL.md (145 lines, YAML frontmatter)
  - references/PROTOCOL.md, FINDING_FORMAT.md, DOD.md, GOTCHAS.md
  - scripts/validate_coverage.py (Python, typed, exit codes)
  - assets/finding-template.json, coverage-template.json (JSON Schema)

**Commands:**
- `/trust review-pr` — main review command
- `/trust init` — interactive onboarding
- `/trust doctor` — health check
- `/trust cleanup` — post-HALT cleanup

**Templates:**
- `trust.config.yaml.template` — setup repo config
- `target.yaml.template` — per-repo target config
- `checklists/security.checklist.md` — 12 starter security rules
- `grounding/06-security-policy.md` — security policy template

**Tests:**
- `tests/e2e/test_mvp.py` — 8 E2E tests, all passing
- `tests/fixtures/` — mock grounding, mock diff with intentional violations

**Profile:** Pilot only (Team/Solo/Enterprise in v2.0)
**Adapters:** Filesystem only (Notion/HTTP in v1.1)
**Agents:** Security only (5 more in v1.0)

### Not yet in this release (see IMPLEMENTATION_PLAN.md)
- Second Pass (Phase 3) — v1.0
- 5 remaining agents — v1.0
- Notion and HTTP adapters — v1.1
- Jira/Spec traceability — v1.2
- Team/Solo/Enterprise profiles — v2.0
