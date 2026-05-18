# Security Policy — {{PROJECT_NAME}}

> **Source of truth** for the TRUST security agent.
> All rules in `checklists/security.checklist.md` reference sections in this document.
> Maintained by: {{SECURITY_OWNER}}
> Last reviewed: {{DATE}}

---

## secrets-management

All secrets — API keys, tokens, passwords, certificates, private keys —
must be managed exclusively through environment variables or an approved
secrets manager (e.g. HashiCorp Vault, AWS Secrets Manager, Doppler).

**What counts as a secret:**
- API keys (third-party services, internal services)
- Database connection strings with credentials
- JWT signing keys / HMAC secrets
- OAuth client secrets
- Private TLS certificates / private keys
- Any value prefixed with `_KEY`, `_SECRET`, `_TOKEN`, `_PASSWORD` by convention

**Logging:** secrets must never appear in log statements, even at DEBUG level.
Log the presence of a value, never its content: `"token present: {bool(token)}"`.

**Scanning:** the CI pipeline runs secret scanning on every PR. A blocked PR
means a secret was detected — rotate the credential immediately.

---

## input-validation

All data entering the system boundary from external sources must be validated
before processing. "External" means: HTTP request bodies/params/headers,
message queue payloads, file uploads, webhook payloads, scheduled job params.

**Validation requirements:**
- Type: validate and coerce to expected type before use
- Length: enforce min/max lengths on all string inputs
- Format: use allowlists, not denylists, for format validation
- Encoding: validate character encoding on text inputs

**Database queries:** all database access must use parameterized queries or
ORM methods that handle parameterization. String interpolation into SQL is
unconditionally forbidden, regardless of how the input was validated upstream.

Approved patterns:
- `db.query("SELECT * FROM t WHERE id = $1", [id])`
- `repository.findById(id)` (ORM, parameterized internally)
- `Model.objects.get(pk=pk)` (Django ORM)

Forbidden patterns:
- `` db.query(`SELECT * FROM t WHERE id = ${id}`) ``
- `db.query("SELECT * FROM t WHERE id = " + id)`
- `cursor.execute(f"SELECT * FROM t WHERE id = {id}")`

---

## output-encoding

Data returned to clients in HTTP responses must be properly encoded
to prevent injection attacks.

- JSON responses: use a JSON serialiser — never concatenate JSON strings manually
- HTML responses: use template engine's auto-escaping — never build HTML by string concatenation
- CSV exports: quote all fields; validate that values don't contain formula injection chars (`=`, `+`, `-`, `@`)

---

## authentication

Every API endpoint must have an explicit authentication requirement.
Authentication must be enforced at the framework/middleware level,
not inside individual handler functions.

Approved authentication methods for this project:
- Bearer JWT tokens validated against the auth service public key
- Session cookies with HttpOnly + Secure flags + SameSite=Strict

Endpoints designed to be public must be annotated explicitly:
`@public` decorator or documented in `03-api-contracts.md`.
The absence of an annotation is NOT sufficient to declare an endpoint public.

---

## authorization

Authentication proves WHO the caller is. Authorization proves what
THAT SPECIFIC CALLER is allowed to do with THAT SPECIFIC RESOURCE.

Both checks are required. A common failure mode is checking that a user
is authenticated but not checking they own the resource they're requesting.

Required pattern:
1. Authenticate — verify token/session
2. Authorise — verify caller's ID matches the resource's owner, or caller has the required role

---

## cryptography

**Approved hashing algorithms:**
- bcrypt (minimum cost factor 12) — for passwords
- argon2id — for passwords (preferred over bcrypt for new code)
- SHA-256 or SHA-3 — for non-password hashing

**Approved encryption:**
- AES-256-GCM — symmetric encryption
- ChaCha20-Poly1305 — symmetric encryption (preferred for variable-length data)
- RSA-OAEP (min 2048-bit) — asymmetric encryption
- ECDH P-256 / X25519 — key exchange

**Explicitly forbidden:**
- MD5 (collision attacks, even for non-security use)
- SHA-1 (deprecated)
- DES / 3DES / RC4 (broken)
- ECB mode (deterministic, pattern-leaking)
- PKCS#1 v1.5 padding for RSA (vulnerable to padding oracle)

If you need to use an algorithm not on the approved list, raise an ADR
before implementing.

---

## network-security

All outbound HTTP calls must use HTTPS (TLS 1.2 minimum, TLS 1.3 preferred).
Certificate validation must never be disabled. `verify=False`,
`ssl.CERT_NONE`, `InsecureRequestWarning` suppression are forbidden.

**CORS:** allowed origins must be explicitly allowlisted per environment.
The wildcard origin (`"*"`) is forbidden in production.
Credentials mode (`withCredentials: true`) requires an explicit origin, never wildcard.

---

## dependency-management

Dependencies introduced or bumped in a PR must not be on the project's
blocked list and must not have CVEs rated CVSS ≥ 7.0 with a known fix.

Run `npm audit` / `pip-audit` / `trivy` locally before pushing if you're
changing dependency files.

---

## error-handling

Client-facing error responses must use generic messages that give no information
about internal system state:

✅ `{"error": "Authentication failed"}` (generic)
❌ `{"error": "User not found in LDAP: uid=jsmith,ou=users,dc=corp,dc=example,dc=com"}` (leaks internal structure)
❌ `{"error": "NullPointerException at com.example.auth.Service:142"}` (leaks stack trace)

Internal error details must be logged server-side with a correlation ID,
and only the correlation ID returned to the client when debugging is needed.
