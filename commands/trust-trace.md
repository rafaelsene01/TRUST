# /trust trace

Inspect and validate traceability for the current branch.

---

## Usage

```
/trust trace check [<branch>]
/trust trace show [<branch>]
```

---

## Commands

### `check` — validate traceability resolution

```bash
/trust trace check
/trust trace check feat/PAY-123
```

Runs the traceability resolution pipeline for the given branch (defaults to
current branch) and prints what was found. Does NOT run a full review — useful
for debugging traceability setup before running `/trust review-pr`.

**Output (success):**

```
🔍 Traceability check — feat/PAY-123
   Ticket ID:   PAY-123
   Source:      spec_file
   Title:       Add payment retry logic
   Status:      In Progress
   Spec file:   ~/work/payments-team-trust/specs/PAY-123.spec.md
   AC found:    yes (3 criteria)
```

**Output (Jira fallback):**

```
🔍 Traceability check — feat/PAY-123
   Ticket ID:   PAY-123
   Source:      jira
   Title:       Add payment retry logic
   Status:      In Review
   URL:         https://empresa.atlassian.net/browse/PAY-123
   AC found:    yes (extracted from description)
```

**Output (not found):**

```
⚠️  Traceability check — feat/PAY-123
   Ticket ID:   PAY-123
   Source:      not_found
   Next action: Create specs/PAY-123.spec.md in your setup repo, or
                configure Jira in trust.config.yaml.
```

**Output (no ticket in branch):**

```
⚠️  No ticket ID found in branch 'feat/no-ticket-here'
   Branch pattern: (?:feat|fix|chore)/({ticket})
   Next action: Rename branch to include ticket ID like feat/PAY-123, or
                adjust branch_pattern in trust.config.yaml.
```

---

### `show` — show last traceability result for current branch

```bash
/trust trace show
/trust trace show feat/PAY-123
```

Reads and prints `traceability.json` from the most recent run for this branch.

---

## Protocol

When `/trust trace check` is invoked:

1. Read `trust.config.yaml` from `$TRUST_SETUP_PATH` and check `traceability.enabled`
2. If not enabled, explain how to enable it and exit
3. Get current branch with `git rev-parse --abbrev-ref HEAD`
4. Import `core/traceability.py` → `run_traceability(branch, findings=[], ...)`
5. Print formatted result (see output examples above)

When `/trust trace show` is invoked:

1. Find most recent run dir for this branch in `$TRUST_SETUP_PATH/runs/`
2. Read `traceability.json` from that run dir
3. Print formatted result

---

## Prerequisites

Traceability must be enabled in `trust.config.yaml`:

```yaml
traceability:
  enabled: true
  jira:
    base_url: "https://empresa.atlassian.net"
    project_keys: ["PAY", "AUTH"]
    auth:
      user_env: "JIRA_USER"
      token_env: "JIRA_TOKEN"
  branch_pattern: "(?:feat|fix|chore)/({ticket})"
  spec_dir: "./specs"
```

And either:
- A spec file at `specs/{TICKET-ID}.spec.md` in the setup repo, **or**
- Jira configured with valid credentials (`JIRA_USER` + `JIRA_TOKEN`)

Run `/trust doctor` to validate the full setup including traceability.
