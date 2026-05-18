# /trust init solo — Setup Protocol

In solo profile, TRUST uses your **second brain as primary grounding source**.
Config lives in `~/.trust-solo/` — no shared repo, no team coordination needed.

## Step 1 — Welcome

```
╭─ TRUST — Solo Mode ──────────────────────────────────────╮
│  Your second brain is your grounding source              │
│  Reviews stay local — zero shared infrastructure needed  │
╰──────────────────────────────────────────────────────────╯
```

## Step 2 — Second brain location

```
🧠 Where is your second brain / knowledge base?
   Detected: ~/Documents/Obsidian
>
```

Save as `TRUST_SECONDBRAIN_PATH`.

## Step 3 — Solo config location

```
📁 Where should I create your solo config?
   Suggested: ~/.trust-solo
>
```

## Step 4 — Product repos

```
🎯 Which repos do you review most?
   (TRUST will detect the active repo at runtime — this is just for presets)

Repo 1 path (optional, press Enter to skip):
>
```

## Step 5 — Generate files

Create at `~/.trust-solo/`:

```
~/.trust-solo/
├── trust.config.yaml       ← profile: solo, secondbrain source
├── .env.local              ← TRUST_SECONDBRAIN_PATH=<path>
├── checklists/             ← personal rules (not shared)
│   └── security.checklist.md
└── runs/
```

`trust.config.yaml` uses `volatile: true` on second-brain sources so
content changes never block a review.

## Step 6 — Print next steps

```
✅ Solo config created at ~/.trust-solo/

📋 Next steps:
   1. export TRUST_SETUP_PATH=~/.trust-solo
   2. Add to your shell rc: export TRUST_SETUP_PATH=~/.trust-solo
   3. /trust doctor
   4. /trust review-pr
```
