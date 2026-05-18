"""Enterprise layer resolver for TRUST v2.0.

In the Enterprise profile the setup is split into three layers:

    corp     (priority 1 — lowest)
             Owned by the platform/security team. Contains company-wide rules,
             security policies, and architecture standards that all teams must
             follow. Changing these requires a platform team PR.

    team     (priority 2)
             Owned by the squad. Contains domain-specific rules, local
             architecture docs, and team conventions. Can override corp rules
             if the override policy allows it (with a recorded reason).

    personal (priority 3 — highest)
             Developer-local. Contains personal second-brain sources and
             per-developer threshold adjustments. Never committed to shared
             repos. Can override team rules with a reason.

Merge semantics:
    - Grounding: higher-priority layer docs with the same path win.
      Docs unique to a layer are always included.
    - Checklists: rules are merged by rule_id. Higher-priority overrides
      are allowed subject to the layer's override_policy.
    - Overrides: recorded in ``overrides.yaml`` per layer. Each entry
      requires a ``reason:`` field when override_policy is
      ``require_reason`` (the default for corp overrides).

Config shape (in enterprise trust.config.yaml):

    ```yaml
    profile_type: enterprise
    layers:
      corp:
        path: ./corp
        priority: 1
        override_policy: require_reason
      team:
        path: ./team
        priority: 2
        override_policy: require_reason
      personal:
        path: ${HOME}/.trust/personal
        priority: 3
        override_policy: allow
    ```
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class LayerOverride:
    """A single rule override declared in a layer's overrides.yaml."""

    rule_id: str
    action: str          # "disable" | "raise_threshold" | "lower_threshold"
    reason: str
    layer: str           # name of the layer declaring this override
    new_threshold: float | None = None   # for raise/lower_threshold actions


@dataclass
class Layer:
    """A single configuration layer in the enterprise profile."""

    name: str                          # "corp" | "team" | "personal"
    path: Path                         # absolute path on disk
    priority: int                      # 1=lowest (corp), 3=highest (personal)
    override_policy: str = "require_reason"   # "allow" | "require_reason" | "deny"


@dataclass
class MergedLayerConfig:
    """Result of merging all enterprise layers."""

    layers: list[Layer]
    grounding_paths: list[tuple[str, str]]   # (source_id, doc_path)
    overrides: list[LayerOverride]
    errors: list[str] = field(default_factory=list)   # policy violations


# ---------------------------------------------------------------------------
# Layer construction
# ---------------------------------------------------------------------------


_DEFAULT_LAYERS = {
    "corp": Layer(name="corp", path=Path("."), priority=1, override_policy="require_reason"),
    "team": Layer(name="team", path=Path("."), priority=2, override_policy="require_reason"),
    "personal": Layer(name="personal", path=Path("."), priority=3, override_policy="allow"),
}


def build_layers(enterprise_cfg: dict, setup_root: Path) -> list[Layer]:
    """Build Layer objects from the enterprise config block.

    Args:
        enterprise_cfg: The ``layers`` sub-dict from trust.config.yaml.
        setup_root:     Root of the enterprise setup repo.

    Returns:
        Sorted list of Layer objects (lowest priority first).
    """
    layers: list[Layer] = []
    layers_cfg = enterprise_cfg.get("layers", {})

    if not isinstance(layers_cfg, dict) or not layers_cfg:
        # Fallback: build defaults from setup_root subdirs
        for name, default in _DEFAULT_LAYERS.items():
            candidate = setup_root / name
            if candidate.is_dir():
                layers.append(
                    Layer(
                        name=name,
                        path=candidate.resolve(),
                        priority=default.priority,
                        override_policy=default.override_policy,
                    )
                )
        return sorted(layers, key=lambda l: l.priority)

    for name, cfg in layers_cfg.items():
        if not isinstance(cfg, dict):
            continue
        raw_path = cfg.get("path", f"./{name}")
        # Expand env vars in path
        expanded = os.path.expandvars(os.path.expanduser(raw_path))
        layer_path = (setup_root / expanded).resolve()

        layers.append(
            Layer(
                name=name,
                path=layer_path,
                priority=int(cfg.get("priority", _DEFAULT_LAYERS.get(name, Layer(name, Path("."), 99)).priority)),
                override_policy=cfg.get("override_policy", "require_reason"),
            )
        )

    return sorted(layers, key=lambda l: l.priority)


# ---------------------------------------------------------------------------
# Grounding merge
# ---------------------------------------------------------------------------


def merge_layer_grounding(layers: list[Layer]) -> list[tuple[str, str, Path]]:
    """Build a list of (source_id, doc_path, layer_path) to load.

    Higher-priority layers win when two layers have a grounding file
    with the same relative path.

    Returns:
        List of (source_id, relative_doc_path, absolute_layer_path) tuples.
    """
    # path → (layer_name, absolute_base)
    seen: dict[str, tuple[str, Path]] = {}

    for layer in sorted(layers, key=lambda l: l.priority):  # low to high
        grounding_dir = layer.path / "grounding"
        if not grounding_dir.is_dir():
            continue
        for doc in grounding_dir.rglob("*.md"):
            rel = doc.relative_to(grounding_dir).as_posix()
            seen[rel] = (layer.name, layer.path)   # higher priority overwrites

    result = []
    for rel_path, (layer_name, base) in seen.items():
        result.append((f"layer-{layer_name}", rel_path, base / "grounding"))

    return result


# ---------------------------------------------------------------------------
# Override loading and merging
# ---------------------------------------------------------------------------


def load_layer_overrides(layer: Layer) -> list[LayerOverride]:
    """Read overrides.yaml from a layer directory.

    Format:
        ```yaml
        overrides:
          - rule_id: SEC-003
            action: disable
            reason: "We use HSM — this control does not apply"
          - rule_id: PERF-001
            action: raise_threshold
            new_threshold: 0.90
            reason: "This domain has strict latency SLAs"
        ```

    Returns empty list if no overrides file exists.
    """
    overrides_file = layer.path / "overrides.yaml"
    if not overrides_file.exists():
        return []

    try:
        text = overrides_file.read_text(encoding="utf-8")
    except OSError:
        return []

    return _parse_overrides_yaml(text, layer.name)


def _parse_overrides_yaml(text: str, layer_name: str) -> list[LayerOverride]:
    """Parse overrides YAML (stdlib, no PyYAML dependency)."""
    overrides: list[LayerOverride] = []
    current: dict = {}

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- rule_id:"):
            if current:
                overrides.append(_dict_to_override(current, layer_name))
            current = {"rule_id": stripped.split(":", 1)[1].strip()}
        elif stripped.startswith("rule_id:") and not current:
            current = {"rule_id": stripped.split(":", 1)[1].strip()}
        elif ":" in stripped and current:
            k, _, v = stripped.partition(":")
            current[k.strip()] = v.strip().strip('"').strip("'")

    if current:
        overrides.append(_dict_to_override(current, layer_name))

    return [o for o in overrides if o.rule_id]


def _dict_to_override(d: dict, layer_name: str) -> LayerOverride:
    new_threshold = d.get("new_threshold")
    if new_threshold is not None:
        try:
            new_threshold = float(new_threshold)
        except (ValueError, TypeError):
            new_threshold = None
    return LayerOverride(
        rule_id=d.get("rule_id", "").upper(),
        action=d.get("action", "disable"),
        reason=d.get("reason", ""),
        layer=layer_name,
        new_threshold=new_threshold,
    )


def merge_layer_overrides(layers: list[Layer]) -> tuple[list[LayerOverride], list[str]]:
    """Merge overrides from all layers. Validate policy compliance.

    Returns:
        (overrides, errors) — errors are policy violations that must be fixed.
    """
    all_overrides: list[LayerOverride] = []
    errors: list[str] = []

    for layer in layers:
        overrides = load_layer_overrides(layer)
        for override in overrides:
            # Policy check
            if layer.override_policy == "deny":
                errors.append(
                    f"Layer '{layer.name}' has override_policy=deny but declares "
                    f"override for {override.rule_id}.\n"
                    f"  Remove the override or change the policy."
                )
                continue
            if layer.override_policy == "require_reason" and not override.reason:
                errors.append(
                    f"Layer '{layer.name}' override for {override.rule_id} "
                    f"requires a reason (override_policy=require_reason).\n"
                    f"  Add: reason: \"<why this override is needed>\""
                )
                continue
            all_overrides.append(override)

    return all_overrides, errors


# ---------------------------------------------------------------------------
# Full merge
# ---------------------------------------------------------------------------


def resolve_layers(enterprise_cfg: dict, setup_root: Path) -> MergedLayerConfig:
    """Build the complete merged layer config for the enterprise profile.

    Args:
        enterprise_cfg: Full trust.config.yaml content as dict.
        setup_root:     Root of the enterprise setup repo.

    Returns:
        MergedLayerConfig with layers, grounding_paths, and overrides.
    """
    layers = build_layers(enterprise_cfg, setup_root)

    grounding_items = merge_layer_grounding(layers)
    grounding_paths = [(source_id, rel_path)
                       for source_id, rel_path, _ in grounding_items]

    overrides, errors = merge_layer_overrides(layers)

    return MergedLayerConfig(
        layers=layers,
        grounding_paths=grounding_paths,
        overrides=overrides,
        errors=errors,
    )
