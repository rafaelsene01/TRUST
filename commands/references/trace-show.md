# /trust trace show — Protocol

Reads and displays the traceability result from the most recent run for a branch.
Does not re-run resolution — reads persisted `traceability.json` only.

## Execution steps

1. Find the most recent run dir for this branch in `$TRUST_SETUP_PATH/runs/`
   - Match by `branch` field in `run-manifest.json`
   - If multiple runs, pick the one with the latest `started_at`
2. Read `traceability.json` from that run dir
3. Print formatted result (same format as `trace check`)

## Edge cases

| Situation | Output |
| --- | --- |
| No runs found for branch | `⚠️  No runs found for branch 'feat/PAY-123'` + suggest running `/trust review-pr` |
| Run found but traceability was skipped | `⏭  Traceability was disabled for this run` |
| `traceability.json` missing | `❌ traceability.json not found in run dir` + suggest re-running review |
