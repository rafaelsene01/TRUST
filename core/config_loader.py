"""Loads and validates trust.config.yaml from the setup repo."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .models import (
    AgentConfig,
    RequiredDoc,
    SourceConfig,
    TrustConfig,
)


class ConfigError(Exception):
    """Raised when trust.config.yaml is invalid or missing."""


def _resolve_env_vars(value: str) -> str:
    """Replace ${VAR:-default} and ${VAR} patterns in a string."""
    import re

    def replacer(match: re.Match) -> str:
        var_expr = match.group(1)
        if ":-" in var_expr:
            var_name, default = var_expr.split(":-", 1)
            return os.environ.get(var_name.strip(), default)
        return os.environ.get(var_expr.strip(), "")

    return re.sub(r"\$\{([^}]+)\}", replacer, value)


def _parse_sources(raw: list[dict[str, Any]]) -> list[SourceConfig]:
    sources = []
    for s in raw:
        base_path = s.get("base_path")
        if base_path:
            base_path = _resolve_env_vars(base_path)
            # Skip optional sources whose env var resolved to empty
            if not base_path and s.get("optional", False):
                continue

        sources.append(
            SourceConfig(
                id=s["id"],
                adapter=s["adapter"],
                base_path=base_path,
                base_url=s.get("base_url"),
                auth_env=s.get("auth_env"),
                volatile=s.get("volatile", False),
                optional=s.get("optional", False),
                cache_ttl_minutes=s.get("cache_ttl_minutes", 60),
            )
        )
    return sources


def _parse_required_docs(raw: list[dict[str, Any]]) -> list[RequiredDoc]:
    return [
        RequiredDoc(
            source=r["source"],
            path=r["path"],
            purpose=r.get("purpose", ""),
        )
        for r in raw
    ]


def _parse_agents(raw: list[dict[str, Any]]) -> list[AgentConfig]:
    agents = []
    for a in raw:
        if isinstance(a, dict) and "id" in a:
            agents.append(
                AgentConfig(
                    id=a["id"],
                    skill=a.get("skill", ""),
                    checklist=a.get("checklist", ""),
                    file_patterns=a.get("file_patterns", ["**/*"]),
                    enabled=a.get("enabled", True),
                )
            )
    return agents


def load_config(setup_path: Path) -> TrustConfig:
    """Load trust.config.yaml from the given setup repo path.

    Args:
        setup_path: Absolute path to the TRUST setup repo root.

    Returns:
        Parsed and validated TrustConfig.

    Raises:
        ConfigError: If the file is missing, unreadable, or invalid.
    """
    config_file = setup_path / "trust.config.yaml"

    if not config_file.exists():
        raise ConfigError(
            f"trust.config.yaml not found at {config_file}.\n"
            f"Run `/trust init pilot` to create a setup repo, or check "
            f"that TRUST_SETUP_PATH points to the correct directory."
        )

    try:
        raw_text = config_file.read_text(encoding="utf-8")
    except PermissionError as e:
        raise ConfigError(f"Cannot read {config_file}: {e}") from e

    try:
        raw: dict[str, Any] = yaml.safe_load(raw_text)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in trust.config.yaml: {e}") from e

    if not isinstance(raw, dict):
        raise ConfigError("trust.config.yaml must be a YAML mapping at the top level.")

    # Required top-level keys
    framework = raw.get("framework", {})
    if not framework.get("name"):
        raise ConfigError("trust.config.yaml: framework.name is required.")

    grounding = raw.get("grounding", {})
    sources_raw = grounding.get("sources", [])
    required_raw = grounding.get("required", [])
    agents_raw = raw.get("agents", [])

    sources = _parse_sources(sources_raw)
    required_docs = _parse_required_docs(required_raw)
    agents = _parse_agents(agents_raw)

    precision_gate = raw.get("precision_gate", {})
    runs = raw.get("runs", {})
    profile = raw.get("profile", {})

    return TrustConfig(
        framework_name=framework.get("name", "TRUST"),
        version=framework.get("version", "1.0.0"),
        mode=framework.get("mode", "strict"),
        profile_type=profile.get("type", "pilot"),
        sources=sources,
        required_docs=required_docs,
        agents=agents,
        confidence_threshold=precision_gate.get("confidence_threshold", 0.80),
        runs_base_dir=runs.get("base_dir", "./runs"),
        retention_policy=runs.get("retention_policy", "audit_failures_only"),
        raw=raw,
    )
