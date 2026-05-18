# /trust review-pr — Execution Protocol

## Step 1 — Resolve environment

```python
import os, subprocess
from pathlib import Path

setup_path = os.environ.get("TRUST_SETUP_PATH", "")
if not setup_path:
    print("❌ TRUST_SETUP_PATH is not set.")
    print("   Run: export TRUST_SETUP_PATH=~/work/your-team-trust")
    exit(1)

print(f"✅ Setup repo: {setup_path}")
```

## Step 2 — Get current branch if not specified

```python
result = subprocess.run(
    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
    capture_output=True, text=True
)
feature_branch = result.stdout.strip()
base_branch = "main"
```

## Step 3 — Run Phases 0-1 via orchestrator

```python
import sys
sys.path.insert(0, str(Path(os.environ["TRUST_SETUP_PATH"]).parent / "trust"))

from core.orchestrator import run_review, resolve_setup_path, resolve_target, capture_diff, parse_diff, load_config
from core.run_manifest import create_manifest, mark_phase_start, mark_phase_done
from pathlib import Path
import json

setup_path = resolve_setup_path()
config = load_config(setup_path)
target_data = resolve_target(setup_path, Path.cwd())
diff_text = capture_diff(base_branch, feature_branch, Path.cwd())
diff_files = parse_diff(diff_text)
```

## Step 4 — Invoke each agent skill

Read `agent-context.json` to know which agents to run, then invoke each one using its SKILL.md.

For each agent in `agent_context["agents_to_run"]`:

- Load the agent's `SKILL.md` as your operational instructions
- Read the grounding documents listed in `grounding.manifest.json`
- Read the diff from `diff.patch`
- Load the agent's checklist from the path specified
- Execute the protocol in `references/PROTOCOL.md`:
  1. Build the coverage matrix (rule × file)
  2. Generate findings for violations
  3. Write `<agents_dir>/<agent_id>.findings.json`
  4. Write `<agents_dir>/<agent_id>.coverage.json`
  5. Fill and write DoD attestation

## Step 5 — Signal completion to orchestrator

```python
from core.orchestrator import (
    _run_phase_4_precision_gate,
    _run_phase_6_traceability_skip,
    _run_phase_7_output,
    finalise_manifest,
    cleanup_run,
)
```

## Output

On success:
```
✅ TRUST review complete — run 2026-05-17-1430-feat-PAY-123

   📋 REVIEW.md: ~/Documents/trust-reviews/api-payments/feat-PAY-123/REVIEW.md

   findings: 4 (1 critical, 2 high, 1 medium)
   silenced: 2 (confidence < 0.80)
   hallucinations intercepted: 0
```

On HALT:
```
❌ TRUST HALT — Phase 1: grounding
   Blocker: Required doc not found: in-setup:06-security-policy.md
   Artifacts preserved at: ~/work/team-trust/runs/2026-05-17-1430-feat-PAY-123/
   Next: /trust doctor
```
