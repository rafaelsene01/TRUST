# /trust doctor --fix — Auto-fix Protocol

Load this file only when `--fix` flag is passed to `/trust doctor`.

## Fixable issues

For each issue detected, apply the fix if it is in this list:

| Issue | Fix |
| --- | --- |
| Missing `TRUST_SETUP_PATH` | Print `export` command and offer to add to shell rc (`~/.zshrc` or `~/.bashrc`) |
| Missing `repo_path` in target | Prompt for path and update `.env.local` |
| Stub grounding doc (< 200 bytes) | Offer to run `/trust map codebase` to populate |

## Non-fixable issues (always manual)

- Missing SKILL.md or broken framework install → re-run `./install.sh`
- Invalid YAML in config or target files → open file and fix manually
- Broken git installation → system-level fix required

## Prompt format for each fix

```
🔧 Auto-fix available: <issue description>
   Proposed fix: <what will happen>
   Apply? [y/n]:
```

Never apply a fix without confirmation. Never modify `trust.config.yaml` directly in `--fix` mode — only `.env.local` and shell rc files.
