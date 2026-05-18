# /trust init enterprise — Setup Protocol

In enterprise profile, TRUST uses a **hierarchical layer structure**:
`corp/` → `team/` → `personal/` — higher-priority layers override lower ones.
Override policy is auditable: each override requires a `reason`.

## Step 1 — Welcome

```
╭─ TRUST — Enterprise Mode ────────────────────────────────╮
│  Three-layer hierarchy: corp → team → personal           │
│  Every override is auditable                             │
╰──────────────────────────────────────────────────────────╯
```

## Step 2 — Enterprise root

```
📁 Where should the enterprise setup live?
   Suggested: ~/work/<company>-trust
>
```

## Step 3 — Layer configuration

```
🏢 Corp layer — organization-wide rules (read-only for teams)
   Path (or press Enter to create empty):
>

👥 Team layer — your team's rules (inherits + overrides corp)
   Team name:
>

👤 Personal layer — your personal overrides (optional)
   Include personal layer? [y/n]:
>
```

## Step 4 — Override policy

```
🔒 Override policy for team → corp:
[1] allow          — teams can override any corp rule silently
[2] require_reason — overrides must include a reason (recommended)
[3] deny           — no overrides allowed
>
```

## Step 5 — Generate files

```
<enterprise_root>/
├── trust.config.yaml       ← profile: enterprise, layers block
├── corp/
│   ├── grounding/
│   ├── checklists/
│   └── overrides.yaml      ← override policy
├── team/
│   ├── grounding/
│   ├── checklists/
│   └── overrides.yaml      ← team overrides with reasons
├── personal/               ← if enabled
│   └── overrides.yaml
└── runs/
```

## Step 6 — Migration from pilot

If migrating from pilot profile, run:
```
python scripts/migrate_pilot_to_enterprise.py \
  --source ~/work/old-team-trust \
  --output <enterprise_root> \
  --dry-run
```

Then review the output and run without `--dry-run`.

## Step 7 — Print next steps

```
✅ Enterprise setup created at <enterprise_root>

📋 Next steps:
   1. Fill corp/grounding/ with org-wide standards
   2. Fill team/grounding/ with team-specific context
   3. Review override policy in corp/overrides.yaml
   4. export TRUST_SETUP_PATH=<enterprise_root>
   5. /trust doctor
```
