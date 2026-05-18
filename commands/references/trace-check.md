# /trust trace check — Protocol

Runs the traceability resolution pipeline for a branch without triggering a full review.
Useful for debugging traceability setup before running `/trust review-pr`.

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

And either a spec file at `specs/{TICKET-ID}.spec.md`, or Jira configured with valid credentials.

## Execution steps

1. Read `trust.config.yaml` from `$TRUST_SETUP_PATH` and check `traceability.enabled`
2. If not enabled, explain how to enable it and exit
3. Get current branch with `git rev-parse --abbrev-ref HEAD` (or use the provided branch arg)
4. Import `core/traceability.py` → `run_traceability(branch, findings=[], ...)`
5. Print formatted result

## Output — success (spec file)

```
🔍 Traceability check — feat/PAY-123
   Ticket ID:   PAY-123
   Source:      spec_file
   Title:       Add payment retry logic
   Status:      In Progress
   Spec file:   ~/work/payments-team-trust/specs/PAY-123.spec.md
   AC found:    yes (3 criteria)
```

## Output — Jira fallback

```
🔍 Traceability check — feat/PAY-123
   Ticket ID:   PAY-123
   Source:      jira
   Title:       Add payment retry logic
   Status:      In Review
   URL:         https://empresa.atlassian.net/browse/PAY-123
   AC found:    yes (extracted from description)
```

## Output — not found

```
⚠️  Traceability check — feat/PAY-123
   Ticket ID:   PAY-123
   Source:      not_found
   Next action: Create specs/PAY-123.spec.md in your setup repo, or
                configure Jira in trust.config.yaml.
```

## Output — no ticket in branch

```
⚠️  No ticket ID found in branch 'feat/no-ticket-here'
   Branch pattern: (?:feat|fix|chore)/({ticket})
   Next action: Rename branch to include ticket ID like feat/PAY-123, or
                adjust branch_pattern in trust.config.yaml.
```
