# Security Checklist

> Source of truth: `grounding/06-security-policy.md`
> Maintained by: {{TEAM_NAME}}
> Last reviewed: {{DATE}}

Each rule must have:
- A unique `rule_id` in the format `SEC-XXX`
- A `source` pointing to a section in the security policy grounding doc
- A clear, testable `title`

---

### SEC-001 — No hardcoded secrets in source code
**Source:** `06-security-policy.md#secrets-management`
**Severity default:** critical

Secrets, API keys, tokens, passwords, and certificates must never appear
in source code. Use environment variables or a secrets manager.

**Applies to:** all files

---

### SEC-002 — No secrets in log statements
**Source:** `06-security-policy.md#secrets-management`
**Severity default:** high

Logging statements must not include tokens, passwords, session IDs,
or personally identifiable information (PII).

**Applies to:** all files

---

### SEC-003 — Input validation on all external data
**Source:** `06-security-policy.md#input-validation`
**Severity default:** high

All data entering the system from external sources (HTTP requests, message queues,
file uploads) must be validated for type, length, and format before processing.

**Applies to:** controller/handler/route files; queue consumers

---

### SEC-004 — Output encoding for user-facing content
**Source:** `06-security-policy.md#output-encoding`
**Severity default:** high

Data returned to clients must be properly encoded to prevent XSS and injection.
Use framework-provided encoding; never build HTML/JSON by concatenation.

**Applies to:** view/template/response files

---

### SEC-005 — Authentication required on non-public endpoints
**Source:** `06-security-policy.md#authentication`
**Severity default:** critical

Every API endpoint must declare its authentication requirement explicitly.
Endpoints without an auth decorator/middleware are assumed to be public —
which must be an intentional, documented decision.

**Applies to:** controller/handler/route files

---

### SEC-006 — Authorization check before accessing resources
**Source:** `06-security-policy.md#authorization`
**Severity default:** critical

After authenticating a request, the code must verify the caller has permission
to access the specific resource (not just any resource of that type).

**Applies to:** service/use-case/handler files

---

### SEC-007 — Parameterized queries for all database access
**Source:** `06-security-policy.md#input-validation`
**Severity default:** critical

All database queries must use parameterized statements or ORM methods that
prevent SQL injection. Raw string interpolation into queries is forbidden.

**Applies to:** all files with DB access

---

### SEC-008 — Approved cryptographic algorithms only
**Source:** `06-security-policy.md#cryptography`
**Severity default:** high

Only cryptographic algorithms from the approved list may be used:
- Hashing: bcrypt (min cost 12), argon2, SHA-256+
- Encryption: AES-256-GCM, ChaCha20-Poly1305
- Forbidden: MD5, SHA-1, DES, RC4, ECB mode

**Applies to:** all files

---

### SEC-009 — HTTPS-only for external communication
**Source:** `06-security-policy.md#network-security`
**Severity default:** high

All outbound HTTP calls must use HTTPS. HTTP URLs in code are forbidden.
Certificate validation must not be disabled.

**Applies to:** HTTP client files, configuration files

---

### SEC-010 — Dependency on patched versions
**Source:** `06-security-policy.md#dependency-management`
**Severity default:** medium

Dependencies introduced or updated in this PR must not pin to versions
with known CVEs. Check against the project's approved dependency policy.

**Applies to:** package.json, go.mod, pom.xml, requirements.txt, etc.

---

### SEC-011 — CORS policy explicitly configured
**Source:** `06-security-policy.md#network-security`
**Severity default:** medium

CORS configuration must allowlist specific origins. Wildcard (`*`) is
forbidden in production builds. Preflight responses must be explicit.

**Applies to:** server/middleware configuration files

---

### SEC-012 — Error messages do not leak internal state
**Source:** `06-security-policy.md#error-handling`
**Severity default:** medium

Error responses returned to clients must use generic messages.
Stack traces, internal paths, SQL queries, and system identifiers
must never be included in client-facing error payloads.

**Applies to:** error handler, middleware, API response files
