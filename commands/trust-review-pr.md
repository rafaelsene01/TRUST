---
description: Run a full TRUST review on a feature branch — loads grounding, executes 6 specialist agents, and generates REVIEW.md
---

# /trust review-pr

Run a full TRUST review on a feature branch.

## Usage

```
/trust review-pr [<feature-branch>] [--base <base-branch>]
```

**Arguments:**
- `feature-branch` — branch to review. Defaults to the current branch.
- `--base` — base branch to diff against. Defaults to `main`.

**Examples:**
```
/trust review-pr feat/PAY-123
/trust review-pr feat/PAY-123 --base develop
/trust review-pr
```

## What this command does

Runs the 8-phase TRUST pipeline: environment setup → grounding → 6 agents → second pass → precision gate → meta-review → traceability → output.

## When to load

| File | When to load |
| --- | --- |
| `commands/references/review-pr-protocol.md` | Before executing — contains the full step-by-step protocol |
