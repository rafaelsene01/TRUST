---
description: Remove os artefatos de uma execução interrompida após investigar e resolver o problema bloqueador
---

# /trust cleanup

Remove a halted run's artifacts after you've investigated and resolved the issue.

## Usage

```
/trust cleanup <run-id>
/trust cleanup --all-halted
```

**Arguments:**
- `run-id` — specific run to clean up (e.g. `2026-05-17-1430-feat-PAY-123`)
- `--all-halted` — clean up ALL runs that have a `.trust-halt` marker

---

## Execution

**Step 1 — Resolve run directory**

```python
import os
from pathlib import Path

setup_path = Path(os.environ["TRUST_SETUP_PATH"])
runs_dir = setup_path / "runs"
run_dir = runs_dir / run_id
```

**Step 2 — Confirm before deleting**

Print:
```
🗑️  About to clean up run: <run-id>

   This run HALTED at: Phase 1 (grounding)
   Blocker: Required doc not found: 06-security-policy.md
   Artifacts: 3 files

   This will permanently remove the run directory.
   Confirm? [y/N]
```

If user confirms: remove the run directory entirely.
If `--all-halted`: show list of halted runs first, then confirm once for all.

**Step 3 — Verify resolved**

Before cleaning, check that the issue that caused the HALT is actually fixed:
- If HALT was "missing grounding doc" → verify the doc now exists
- If HALT was "coverage incomplete" → note that the issue was in the agent, not config

Print a warning if the original blocker might still be present:
```
⚠️  Warning: The original blocker was "missing doc: 06-security-policy.md"
   That file still doesn't exist. Are you sure the issue is resolved?
   Run /trust doctor to verify before cleaning.
```

**Step 4 — Clean**

```python
import shutil
shutil.rmtree(run_dir)
print(f"✅ Cleaned run {run_id}")
print(f"   Run /trust review-pr to retry.")
```
