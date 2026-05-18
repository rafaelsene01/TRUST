"""Profile registry for TRUST v2.0 — Multi-Profile support.

TRUST supports four deployment profiles that differ in how the setup
configuration is stored and who owns it:

    pilot      — Setup repo is separate from the product repo (current default).
                 One team maintains a dedicated ``<team>-trust`` repo and
                 points to it via ``$TRUST_SETUP_PATH``.

    team       — Setup lives inside the product repo at ``.trust/``.
                 No separate repo; no ``TRUST_SETUP_PATH`` needed.
                 Everyone on the team uses the same setup via git.

    solo       — Developer-local setup at ``~/.trust/user.config.yaml``.
                 Intended for individual use with a personal second-brain
                 (Notion, Obsidian) as the primary grounding source.

    enterprise — Three-layer hierarchy: corp → team → personal.
                 Each layer has its own grounding, checklists, and config.
                 Higher-priority layers can override lower-priority rules.
                 Every override is auditable (reason required by policy).

Detection order (``detect_profile``):
    1. ``trust.config.yaml`` declares ``profile_type:`` → use it
    2. ``.trust/`` directory present in CWD → ``team``
    3. ``TRUST_SETUP_PATH`` env var set → inspect that config → ``pilot`` or
       ``enterprise`` depending on ``profile_type`` in the config
    4. ``~/.trust/user.config.yaml`` exists → ``solo``
    5. Default: ``pilot`` (requires ``TRUST_SETUP_PATH``)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


# ---------------------------------------------------------------------------
# Enums and data structures
# ---------------------------------------------------------------------------


class ProfileType(str, Enum):
    PILOT = "pilot"
    TEAM = "team"
    SOLO = "solo"
    ENTERPRISE = "enterprise"


@dataclass
class ProfileConfig:
    """Resolved profile configuration."""

    profile_type: ProfileType
    setup_root: Path          # where trust.config.yaml lives
    product_root: Path        # git repository root (CWD by default)
    layers: list[dict] = field(default_factory=list)   # enterprise only


# ---------------------------------------------------------------------------
# Profile detection
# ---------------------------------------------------------------------------


def detect_profile(cwd: Path | None = None) -> tuple[ProfileType, Path]:
    """Detect the active profile from the environment and filesystem.

    Returns:
        (profile_type, setup_root) — setup_root is where trust.config.yaml is.

    Raises:
        ValueError: if no valid profile can be detected.
    """
    if cwd is None:
        cwd = Path.cwd()

    # 1. .trust/ inside the product repo → team profile
    team_root = cwd / ".trust"
    if team_root.is_dir() and (team_root / "trust.config.yaml").exists():
        return ProfileType.TEAM, team_root

    # 2. TRUST_SETUP_PATH set → pilot or enterprise
    trust_setup_raw = os.environ.get("TRUST_SETUP_PATH", "").strip()
    if trust_setup_raw:
        setup_path = Path(trust_setup_raw).expanduser().resolve()
        if setup_path.is_dir():
            declared = _read_profile_type(setup_path / "trust.config.yaml")
            if declared == ProfileType.ENTERPRISE:
                return ProfileType.ENTERPRISE, setup_path
            return ProfileType.PILOT, setup_path

    # 3. Solo: ~/.trust/user.config.yaml
    try:
        solo_config = Path.home() / ".trust" / "user.config.yaml"
        solo_exists = solo_config.exists()
    except (RuntimeError, OSError):
        solo_exists = False
    if solo_exists:
        return ProfileType.SOLO, solo_config.parent

    # 4. Default → pilot (caller must provide TRUST_SETUP_PATH or will fail)
    if trust_setup_raw:
        setup_path = Path(trust_setup_raw).expanduser().resolve()
        return ProfileType.PILOT, setup_path

    raise ValueError(
        "Could not detect a TRUST profile.\n"
        "  Options:\n"
        "    • Set TRUST_SETUP_PATH to a pilot/enterprise setup repo\n"
        "    • Create .trust/trust.config.yaml in the product repo (team profile)\n"
        "    • Create ~/.trust/user.config.yaml (solo profile)\n"
        "  Run /trust init to create a new setup."
    )


def _read_profile_type(config_path: Path) -> ProfileType | None:
    """Read profile_type from a trust.config.yaml. Returns None on error."""
    if not config_path.exists():
        return None
    try:
        text = config_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip().startswith("profile_type:"):
                _, _, raw = line.partition(":")
                val = raw.strip().strip('"').strip("'")
                try:
                    return ProfileType(val)
                except ValueError:
                    return None
    except OSError:
        return None
    return None


# ---------------------------------------------------------------------------
# Profile resolution
# ---------------------------------------------------------------------------


def resolve_profile(cwd: Path | None = None) -> ProfileConfig:
    """Detect and validate the active profile. Returns a ProfileConfig.

    Raises:
        ValueError: if detection fails or required paths are missing.
    """
    if cwd is None:
        cwd = Path.cwd()

    profile_type, setup_root = detect_profile(cwd)

    enterprise_layers: list[dict] = []
    if profile_type == ProfileType.ENTERPRISE:
        enterprise_layers = _load_enterprise_layers(setup_root)

    return ProfileConfig(
        profile_type=profile_type,
        setup_root=setup_root,
        product_root=cwd,
        layers=enterprise_layers,
    )


def _load_enterprise_layers(setup_root: Path) -> list[dict]:
    """Read the enterprise layers block from trust.config.yaml."""
    config_path = setup_root / "trust.config.yaml"
    if not config_path.exists():
        return []
    try:
        # Simple YAML subset reader — avoids requiring PyYAML
        text = config_path.read_text(encoding="utf-8")
        import re
        # Find layers: block
        m = re.search(r"^layers:\s*\n((?:  .+\n)*)", text, re.MULTILINE)
        if not m:
            return []
        # Parse each layer line: "  - name: corp  path: ./corp  priority: 1"
        layers = []
        for line in m.group(1).splitlines():
            line = line.strip().lstrip("- ")
            if not line:
                continue
            entry: dict = {}
            for part in line.split():
                if ":" in part:
                    k, _, v = part.partition(":")
                    entry[k] = v
            if entry:
                layers.append(entry)
        return layers
    except OSError:
        return []


# ---------------------------------------------------------------------------
# Profile validation
# ---------------------------------------------------------------------------


def validate_profile(profile_type: ProfileType, setup_root: Path) -> list[str]:
    """Return a list of validation errors for the given profile.

    Empty list = valid.
    """
    errors: list[str] = []

    if not setup_root.exists():
        errors.append(
            f"Setup root does not exist: {setup_root}\n"
            f"  Run /trust init {profile_type.value} to create it."
        )
        return errors

    config_file = setup_root / "trust.config.yaml"
    if not config_file.exists():
        errors.append(
            f"Missing trust.config.yaml at {config_file}\n"
            f"  Copy a template: cp ~/.trust/templates/profiles/"
            f"{profile_type.value}/trust.config.yaml.template {config_file}"
        )

    if profile_type in (ProfileType.PILOT, ProfileType.TEAM):
        grounding = setup_root / "grounding"
        if not grounding.is_dir():
            errors.append(
                f"Missing grounding/ directory at {grounding}\n"
                f"  Create it and add at least one .md file."
            )
        targets = setup_root / "targets"
        if profile_type == ProfileType.PILOT and not targets.is_dir():
            errors.append(
                f"Missing targets/ directory at {targets}\n"
                f"  Add a target with /trust target add <repo-path>"
            )

    if profile_type == ProfileType.ENTERPRISE:
        for layer_name in ("corp", "team"):
            layer_path = setup_root / layer_name
            if not layer_path.is_dir():
                errors.append(
                    f"Missing '{layer_name}' layer directory: {layer_path}\n"
                    f"  Run /trust init enterprise to scaffold the layer structure."
                )

    return errors


def profile_summary(cfg: ProfileConfig) -> str:
    """One-line summary of the active profile for diagnostic output."""
    icons = {
        ProfileType.PILOT: "🧪",
        ProfileType.TEAM: "👥",
        ProfileType.SOLO: "👤",
        ProfileType.ENTERPRISE: "🏢",
    }
    icon = icons.get(cfg.profile_type, "•")
    return (
        f"{icon} Profile: {cfg.profile_type.value}  "
        f"setup: {cfg.setup_root}  product: {cfg.product_root}"
    )
