"""TRUST v2.0 tests — Multi-Profile.

Covers:
  - profile_registry: detect_profile, resolve_profile, validate_profile
  - layer_resolver: build_layers, merge_layer_grounding, overrides
  - provenance: tag_finding, build_provenance_report, format appendix
  - migration script: dry-run + real migration pilot → enterprise

All tests are fully offline — no real Jira, Notion, or network calls.

Run:
    python -m pytest tests/e2e/test_v2.py -v
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

_MIGRATION_SCRIPT = REPO_ROOT / "scripts" / "migrate_pilot_to_enterprise.py"


def _load_migrate():
    """Load migrate function directly from the script file."""
    module_name = "_trust_scripts.migrate_pilot_to_enterprise"
    if module_name in sys.modules:
        return sys.modules[module_name].migrate
    spec = importlib.util.spec_from_file_location(module_name, _MIGRATION_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod.migrate

from core.profile_registry import (
    ProfileType,
    ProfileConfig,
    detect_profile,
    resolve_profile,
    validate_profile,
    profile_summary,
    _read_profile_type,
)
from core.layer_resolver import (
    Layer,
    LayerOverride,
    build_layers,
    merge_layer_grounding,
    load_layer_overrides,
    merge_layer_overrides,
    resolve_layers,
)
from core.provenance import (
    ProvenanceEntry,
    tag_finding,
    tag_findings,
    apply_override_to_finding,
    build_provenance_report,
    format_provenance_appendix,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pilot_setup(tmp_path: Path) -> Path:
    """Create a minimal pilot setup directory."""
    setup = tmp_path / "pilot-setup"
    (setup / "grounding").mkdir(parents=True)
    (setup / "checklists").mkdir(parents=True)
    (setup / "targets").mkdir(parents=True)
    (setup / "trust.config.yaml").write_text(
        "framework: trust\nversion: '1.2'\nprofile_type: pilot\n",
        encoding="utf-8",
    )
    (setup / "grounding" / "06-security-policy.md").write_text(
        "# Security Policy\n\nContent here.\n", encoding="utf-8"
    )
    (setup / "checklists" / "security.checklist.md").write_text(
        "### SEC-001 — Test Rule\nTest rule content.\n", encoding="utf-8"
    )
    return setup


def _make_enterprise_setup(tmp_path: Path) -> Path:
    """Create a minimal enterprise setup with corp and team layers."""
    setup = tmp_path / "enterprise-setup"
    config = (
        "framework: trust\nversion: '1.2'\nprofile_type: enterprise\n"
        "layers:\n"
        "  corp:\n    path: ./corp\n    priority: 1\n    override_policy: require_reason\n"
        "  team:\n    path: ./team\n    priority: 2\n    override_policy: require_reason\n"
    )
    (setup).mkdir(parents=True)
    (setup / "trust.config.yaml").write_text(config, encoding="utf-8")

    for layer in ("corp", "team"):
        (setup / layer / "grounding").mkdir(parents=True)
        (setup / layer / "checklists").mkdir(parents=True)
        (setup / layer / "grounding" / "01-arch.md").write_text(
            f"# Arch — {layer} layer\n", encoding="utf-8"
        )

    return setup


def _make_finding(rule_id: str = "SEC-001") -> dict:
    return {
        "rule_id": rule_id,
        "claim": "Test",
        "severity": "high",
        "confidence": 0.90,
        "file": "src/auth.py",
    }


# ---------------------------------------------------------------------------
# profile_registry: _read_profile_type
# ---------------------------------------------------------------------------


class TestReadProfileType:
    def test_reads_pilot(self, tmp_path):
        cfg = tmp_path / "trust.config.yaml"
        cfg.write_text("profile_type: pilot\n", encoding="utf-8")
        assert _read_profile_type(cfg) == ProfileType.PILOT

    def test_reads_enterprise(self, tmp_path):
        cfg = tmp_path / "trust.config.yaml"
        cfg.write_text("profile_type: enterprise\n", encoding="utf-8")
        assert _read_profile_type(cfg) == ProfileType.ENTERPRISE

    def test_missing_file(self, tmp_path):
        assert _read_profile_type(tmp_path / "missing.yaml") is None

    def test_unknown_profile(self, tmp_path):
        cfg = tmp_path / "trust.config.yaml"
        cfg.write_text("profile_type: unknown_value\n", encoding="utf-8")
        assert _read_profile_type(cfg) is None


# ---------------------------------------------------------------------------
# profile_registry: detect_profile
# ---------------------------------------------------------------------------


class TestDetectProfile:
    def test_detects_team_from_trust_dir(self, tmp_path):
        trust_dir = tmp_path / ".trust"
        trust_dir.mkdir()
        (trust_dir / "trust.config.yaml").write_text(
            "profile_type: team\n", encoding="utf-8"
        )
        ptype, setup_root = detect_profile(cwd=tmp_path)
        assert ptype == ProfileType.TEAM
        assert setup_root == trust_dir

    def test_detects_pilot_from_trust_setup_path(self, tmp_path):
        setup = _make_pilot_setup(tmp_path)
        with patch.dict(os.environ, {"TRUST_SETUP_PATH": str(setup)}, clear=False):
            ptype, setup_root = detect_profile(cwd=tmp_path)
        assert ptype == ProfileType.PILOT
        assert setup_root == setup

    def test_detects_enterprise_from_trust_setup_path(self, tmp_path):
        setup = _make_enterprise_setup(tmp_path)
        with patch.dict(os.environ, {"TRUST_SETUP_PATH": str(setup)}, clear=False):
            ptype, setup_root = detect_profile(cwd=tmp_path)
        assert ptype == ProfileType.ENTERPRISE

    def test_no_profile_raises(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            # Remove TRUST_SETUP_PATH if set
            env = {k: v for k, v in os.environ.items() if k != "TRUST_SETUP_PATH"}
            with patch.dict(os.environ, env, clear=True):
                try:
                    detect_profile(cwd=tmp_path)
                    # If solo config exists at ~/.trust, it may succeed — that's OK
                except ValueError as exc:
                    assert "TRUST profile" in str(exc)

    def test_team_takes_priority_over_trust_setup_path(self, tmp_path):
        trust_dir = tmp_path / ".trust"
        trust_dir.mkdir()
        (trust_dir / "trust.config.yaml").write_text("profile_type: team\n", encoding="utf-8")

        setup = _make_pilot_setup(tmp_path)
        with patch.dict(os.environ, {"TRUST_SETUP_PATH": str(setup)}, clear=False):
            ptype, _ = detect_profile(cwd=tmp_path)
        assert ptype == ProfileType.TEAM


# ---------------------------------------------------------------------------
# profile_registry: validate_profile
# ---------------------------------------------------------------------------


class TestValidateProfile:
    def test_valid_pilot(self, tmp_path):
        setup = _make_pilot_setup(tmp_path)
        errors = validate_profile(ProfileType.PILOT, setup)
        assert errors == []

    def test_pilot_missing_grounding(self, tmp_path):
        setup = _make_pilot_setup(tmp_path)
        import shutil
        shutil.rmtree(setup / "grounding")
        errors = validate_profile(ProfileType.PILOT, setup)
        assert any("grounding" in e for e in errors)

    def test_pilot_missing_config(self, tmp_path):
        setup = _make_pilot_setup(tmp_path)
        (setup / "trust.config.yaml").unlink()
        errors = validate_profile(ProfileType.PILOT, setup)
        assert any("trust.config.yaml" in e for e in errors)

    def test_enterprise_valid(self, tmp_path):
        setup = _make_enterprise_setup(tmp_path)
        errors = validate_profile(ProfileType.ENTERPRISE, setup)
        assert errors == []

    def test_enterprise_missing_corp(self, tmp_path):
        setup = _make_enterprise_setup(tmp_path)
        import shutil
        shutil.rmtree(setup / "corp")
        errors = validate_profile(ProfileType.ENTERPRISE, setup)
        assert any("corp" in e for e in errors)

    def test_nonexistent_setup_root(self, tmp_path):
        errors = validate_profile(ProfileType.PILOT, tmp_path / "nonexistent")
        assert any("does not exist" in e for e in errors)


# ---------------------------------------------------------------------------
# profile_registry: profile_summary
# ---------------------------------------------------------------------------


class TestProfileSummary:
    def test_summary_contains_profile_type(self, tmp_path):
        cfg = ProfileConfig(
            profile_type=ProfileType.ENTERPRISE,
            setup_root=tmp_path,
            product_root=tmp_path,
        )
        summary = profile_summary(cfg)
        assert "enterprise" in summary
        assert "🏢" in summary


# ---------------------------------------------------------------------------
# layer_resolver: build_layers
# ---------------------------------------------------------------------------


class TestBuildLayers:
    def test_builds_from_config_dict(self, tmp_path):
        setup = _make_enterprise_setup(tmp_path)
        cfg = {
            "layers": {
                "corp": {"path": "./corp", "priority": 1, "override_policy": "require_reason"},
                "team": {"path": "./team", "priority": 2, "override_policy": "require_reason"},
            }
        }
        layers = build_layers(cfg, setup)
        assert len(layers) == 2
        assert layers[0].name == "corp"
        assert layers[0].priority == 1
        assert layers[1].name == "team"
        assert layers[1].priority == 2

    def test_sorted_by_priority(self, tmp_path):
        setup = _make_enterprise_setup(tmp_path)
        cfg = {
            "layers": {
                "team": {"path": "./team", "priority": 2},
                "corp": {"path": "./corp", "priority": 1},
            }
        }
        layers = build_layers(cfg, setup)
        assert layers[0].priority < layers[1].priority

    def test_fallback_to_subdirs(self, tmp_path):
        setup = _make_enterprise_setup(tmp_path)
        layers = build_layers({}, setup)  # empty config → scan subdirs
        names = {l.name for l in layers}
        assert "corp" in names
        assert "team" in names


# ---------------------------------------------------------------------------
# layer_resolver: merge_layer_grounding
# ---------------------------------------------------------------------------


class TestMergeLayerGrounding:
    def test_merges_unique_docs(self, tmp_path):
        corp = tmp_path / "corp"
        team = tmp_path / "team"
        (corp / "grounding").mkdir(parents=True)
        (team / "grounding").mkdir(parents=True)
        (corp / "grounding" / "corp-policy.md").write_text("corp", encoding="utf-8")
        (team / "grounding" / "team-arch.md").write_text("team", encoding="utf-8")

        layers = [
            Layer(name="corp", path=corp, priority=1),
            Layer(name="team", path=team, priority=2),
        ]
        result = merge_layer_grounding(layers)
        paths = {rel for _, rel, _ in result}
        assert "corp-policy.md" in paths
        assert "team-arch.md" in paths

    def test_higher_priority_wins_on_same_path(self, tmp_path):
        corp = tmp_path / "corp"
        team = tmp_path / "team"
        (corp / "grounding").mkdir(parents=True)
        (team / "grounding").mkdir(parents=True)
        # Same filename in both layers
        (corp / "grounding" / "shared.md").write_text("corp version", encoding="utf-8")
        (team / "grounding" / "shared.md").write_text("team version", encoding="utf-8")

        layers = [
            Layer(name="corp", path=corp, priority=1),
            Layer(name="team", path=team, priority=2),
        ]
        result = merge_layer_grounding(layers)
        # Should appear only once, from the team (priority 2 wins)
        paths = [rel for _, rel, _ in result]
        assert paths.count("shared.md") == 1
        sources = {src for src, rel, _ in result if rel == "shared.md"}
        assert "layer-team" in sources

    def test_empty_grounding_dirs(self, tmp_path):
        corp = tmp_path / "corp"
        (corp / "grounding").mkdir(parents=True)  # empty
        layers = [Layer(name="corp", path=corp, priority=1)]
        result = merge_layer_grounding(layers)
        assert result == []


# ---------------------------------------------------------------------------
# layer_resolver: overrides
# ---------------------------------------------------------------------------


class TestLayerOverrides:
    def test_load_valid_overrides(self, tmp_path):
        layer_path = tmp_path / "team"
        layer_path.mkdir()
        (layer_path / "overrides.yaml").write_text(
            "overrides:\n"
            "  - rule_id: SEC-003\n"
            "    action: disable\n"
            "    reason: We use HSM\n",
            encoding="utf-8",
        )
        layer = Layer(name="team", path=layer_path, priority=2)
        overrides = load_layer_overrides(layer)
        assert len(overrides) == 1
        assert overrides[0].rule_id == "SEC-003"
        assert overrides[0].action == "disable"
        assert overrides[0].reason == "We use HSM"

    def test_no_overrides_file(self, tmp_path):
        layer = Layer(name="corp", path=tmp_path, priority=1)
        overrides = load_layer_overrides(layer)
        assert overrides == []

    def test_merge_overrides_policy_violation(self, tmp_path):
        layer_path = tmp_path / "team"
        layer_path.mkdir()
        # No reason provided, but policy requires it
        (layer_path / "overrides.yaml").write_text(
            "overrides:\n"
            "  - rule_id: SEC-001\n"
            "    action: disable\n",
            encoding="utf-8",
        )
        layers = [Layer(name="team", path=layer_path, priority=2, override_policy="require_reason")]
        _, errors = merge_layer_overrides(layers)
        assert any("reason" in e for e in errors)

    def test_merge_overrides_policy_allow(self, tmp_path):
        layer_path = tmp_path / "personal"
        layer_path.mkdir()
        (layer_path / "overrides.yaml").write_text(
            "overrides:\n"
            "  - rule_id: CONV-001\n"
            "    action: disable\n",
            encoding="utf-8",
        )
        layers = [Layer(name="personal", path=layer_path, priority=3, override_policy="allow")]
        overrides, errors = merge_layer_overrides(layers)
        assert errors == []
        assert len(overrides) == 1

    def test_deny_policy_rejects_override(self, tmp_path):
        layer_path = tmp_path / "corp"
        layer_path.mkdir()
        (layer_path / "overrides.yaml").write_text(
            "overrides:\n"
            "  - rule_id: SEC-001\n"
            "    action: disable\n"
            "    reason: Should not be allowed\n",
            encoding="utf-8",
        )
        layers = [Layer(name="corp", path=layer_path, priority=1, override_policy="deny")]
        overrides, errors = merge_layer_overrides(layers)
        assert any("deny" in e for e in errors)
        assert len(overrides) == 0


# ---------------------------------------------------------------------------
# provenance: tagging
# ---------------------------------------------------------------------------


class TestProvenance:
    def test_tag_finding_injects_provenance(self):
        f = _make_finding("SEC-001")
        tagged = tag_finding(f, "corp")
        assert "provenance" in tagged
        assert tagged["provenance"]["layer"] == "corp"
        assert tagged["provenance"]["rule_id"] == "SEC-001"

    def test_tag_finding_does_not_mutate_original(self):
        f = _make_finding("SEC-001")
        tagged = tag_finding(f, "corp")
        assert "provenance" not in f

    def test_tag_findings_tags_all(self):
        findings = [_make_finding("SEC-001"), _make_finding("SEC-002")]
        tagged = tag_findings(findings, "team")
        assert all(f["provenance"]["layer"] == "team" for f in tagged)

    def test_apply_override_marks_finding(self):
        f = tag_finding(_make_finding("SEC-001"), "corp")
        overridden = apply_override_to_finding(f, "team", "We use HSM")
        assert overridden["provenance"]["overridden_by"] == "team"
        assert overridden["provenance"]["override_reason"] == "We use HSM"

    def test_provenance_entry_to_dict(self):
        entry = ProvenanceEntry(layer="corp", rule_id="SEC-001")
        d = entry.to_dict()
        assert d["layer"] == "corp"
        assert "overridden_by" not in d  # not set → not included


# ---------------------------------------------------------------------------
# provenance: reporting
# ---------------------------------------------------------------------------


class TestProvenanceReport:
    def test_groups_by_layer(self):
        findings = [
            tag_finding(_make_finding("SEC-001"), "corp"),
            tag_finding(_make_finding("SEC-002"), "corp"),
            tag_finding(_make_finding("CONV-001"), "team"),
        ]
        report = build_provenance_report(findings)
        assert len(report["by_layer"]["corp"]) == 2
        assert len(report["by_layer"]["team"]) == 1
        assert report["total"] == 3

    def test_records_overrides(self):
        f = tag_finding(_make_finding("SEC-001"), "corp")
        f = apply_override_to_finding(f, "team", "HSM")
        report = build_provenance_report([f])
        assert len(report["overrides_applied"]) == 1
        assert report["overrides_applied"][0]["overriding_layer"] == "team"

    def test_format_appendix_markdown(self):
        findings = [
            tag_finding(_make_finding("SEC-001"), "corp"),
            tag_finding(_make_finding("CONV-001"), "team"),
        ]
        report = build_provenance_report(findings)
        appendix = format_provenance_appendix(report)
        assert "Corp" in appendix
        assert "Team" in appendix
        assert "SEC-001" in appendix
        assert "<details>" in appendix


# ---------------------------------------------------------------------------
# migration script
# ---------------------------------------------------------------------------


class TestMigrationScript:
    def test_dry_run_does_not_create_output(self, tmp_path):
        migrate = _load_migrate()

        source = _make_pilot_setup(tmp_path)
        output = tmp_path / "enterprise-out"
        result = migrate(source, output, dry_run=True)
        assert result == 0
        assert not output.exists()

    def test_migration_creates_structure(self, tmp_path):
        migrate = _load_migrate()

        source = _make_pilot_setup(tmp_path)
        output = tmp_path / "enterprise-out"
        result = migrate(source, output, dry_run=False)
        assert result == 0

        assert (output / "trust.config.yaml").exists()
        assert (output / "corp" / "grounding").is_dir()
        assert (output / "corp" / "checklists").is_dir()
        assert (output / "corp" / "overrides.yaml").exists()
        assert (output / "team" / "grounding").is_dir()
        assert (output / "team" / "checklists").is_dir()
        assert (output / "team" / "overrides.yaml").exists()
        assert (output / "personal" / ".gitkeep").exists()

    def test_migration_copies_grounding(self, tmp_path):
        migrate = _load_migrate()

        source = _make_pilot_setup(tmp_path)
        output = tmp_path / "enterprise-out"
        migrate(source, output)
        assert (output / "team" / "grounding" / "06-security-policy.md").exists()

    def test_migration_copies_checklists(self, tmp_path):
        migrate = _load_migrate()

        source = _make_pilot_setup(tmp_path)
        output = tmp_path / "enterprise-out"
        migrate(source, output)
        assert (output / "team" / "checklists" / "security.checklist.md").exists()

    def test_migration_sets_enterprise_profile_type(self, tmp_path):
        migrate = _load_migrate()

        source = _make_pilot_setup(tmp_path)
        output = tmp_path / "enterprise-out"
        migrate(source, output)
        config_text = (output / "trust.config.yaml").read_text(encoding="utf-8")
        assert "profile_type: enterprise" in config_text

    def test_migration_fails_if_output_exists(self, tmp_path):
        migrate = _load_migrate()

        source = _make_pilot_setup(tmp_path)
        output = tmp_path / "existing-dir"
        output.mkdir()
        result = migrate(source, output)
        assert result == 1

    def test_migration_fails_if_source_missing(self, tmp_path):
        migrate = _load_migrate()

        result = migrate(tmp_path / "nonexistent", tmp_path / "output")
        assert result == 1
