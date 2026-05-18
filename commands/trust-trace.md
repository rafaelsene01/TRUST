# /trust trace

Inspect and validate traceability for the current branch.

## Usage

```
/trust trace check [<branch>]
/trust trace show [<branch>]
```

## Subcommands

| Subcommand | What it does |
| --- | --- |
| `check` | Runs traceability resolution without a full review — useful for debugging setup |
| `show` | Reads and prints the traceability result from the most recent run for this branch |

## Prerequisites

Traceability must be enabled in `trust.config.yaml`. Run `/trust doctor` to validate.

## When to load

| File | When to load |
| --- | --- |
| `commands/references/trace-check.md` | Subcommand is `check` — contains protocol, prereqs, and output formats |
| `commands/references/trace-show.md` | Subcommand is `show` |
