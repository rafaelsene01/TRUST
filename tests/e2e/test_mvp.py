"""End-to-end MVP test for the TRUST framework.

Tests the complete pipeline with a mock setup repo and a mock diff
containing intentional security violations.

Run:
    python -m pytest tests/e2e/test_mvp.py -v

Or standalone:
    python tests/e2e/test_mvp.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.config_loader import load_config
from core.grounding_loader import load_grounding, validate_grounding_dod
from core.halt_handler import HaltError
from core.run_manifest import create_manifest, save_manifest
from adapters.filesystem_adapter import FilesystemAdapter
import sys, os; sys.path.insert(0, str(REPO_ROOT / "skills" / "trust-security-review")); from scripts.validate_coverage import validate_coverage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent / "fixtures"
MOCK_GROUNDING = FIXTURES / "mock-grounding"
MOCK_DIFF = FIXTURES / "mock-diff" / "feat-PAY-123.patch"
CHECKLIST = Path(__file__).parent.parent.parent / "templates" / "checklists" / "security.checklist.md"


def build_mock_setup(tmp_dir: Path) -> Path:
    """Create a minimal setup repo structure for testing."""
    setup = tmp_dir / "mock-setup"
    setup.mkdir()

    # grounding/
    grounding_dir = setup / "grounding"
    shutil.copytree(MOCK_GROUNDING, grounding_dir)

    # checklists/
    checklists_dir = setup / "checklists"
    checklists_dir.mkdir()
    shutil.copy(CHECKLIST, checklists_dir / "security.checklist.md")

    # runs/
    (setup / "runs").mkdir()

    # targets/
    targets_dir = setup / "targets"
    targets_dir.mkdir()
    (targets_dir / "mock-product.yaml").write_text(
        """
target:
  id: "mock-product"
  name: "Mock Product"
  remote_url: "git@github.com:empresa/mock-product.git"
  repo_path: "/tmp/mock-product"
  default_branch: "main"
applied_agents:
  - id: "security"
    enabled: true
output:
  comment_on_pr: false
""",
        encoding="utf-8",
    )

    # trust.config.yaml
    (setup / "trust.config.yaml").write_text(
        f"""
framework:
  name: "TRUST"
  version: "1.0.0"
  mode: "strict"

profile:
  type: "pilot"
  team_name: "Test Team"

grounding:
  sources:
    - id: "in-setup"
      adapter: "filesystem"
      base_path: "./grounding"
      volatile: false

  required:
    - source: "in-setup"
      path: "01-architecture.md"
    - source: "in-setup"
      path: "02-domain-glossary.md"
    - source: "in-setup"
      path: "03-api-contracts.md"
    - source: "in-setup"
      path: "04-data-model.md"
    - source: "in-setup"
      path: "05-conventions.md"
    - source: "in-setup"
      path: "06-security-policy.md"
    - source: "in-setup"
      path: "07-adrs.md"

  dod:
    all_required_loaded: true
    min_total_bytes: 5000

agents:
  - id: "security"
    skill: "./skills/trust-security-review/SKILL.md"
    checklist: "./checklists/security.checklist.md"
    file_patterns: ["**/*"]
    enabled: true

precision_gate:
  confidence_threshold: 0.80

meta_review:
  enabled: true
  validation_checks:
    - "file_exists_in_diff"
    - "evidence_quote_is_literal"

traceability:
  enabled: false

output:
  default_path: "/tmp/trust-test-reviews"
  ai_never_approves_or_rejects: true

runs:
  base_dir: "./runs"
  retention_policy: "audit_failures_only"
""",
        encoding="utf-8",
    )

    return setup


def make_mock_findings(run_dir: Path) -> None:
    """Write mock findings as if the security agent had executed."""
    agents_dir = run_dir / "agents"
    agents_dir.mkdir(exist_ok=True)

    diff_text = MOCK_DIFF.read_text(encoding="utf-8")

    findings = [
        {
            "agent": "security",
            "rule_id": "SEC-007",
            "rule_source": "in-setup:06-security-policy.md#input-validation",
            "file": "src/auth/login.ts",
            "line_start": 8,
            "line_end": 8,
            "severity": "critical",
            "confidence": 0.98,
            "claim": "User input concatenated directly into SQL query — SQL injection.",
            # This MUST be literal to pass meta-review
            "evidence_quote": "    const user = await db.query(`SELECT * FROM users WHERE email='${email}'`);",
            "why_it_matters": "Per 06-security-policy.md#input-validation: parameterized queries required in 100% of DB access.",
            "suggestion": "const user = await db.query('SELECT * FROM users WHERE email = $1', [email]);",
            "false_positive_risk": "low",
            "false_positive_reason": None,
        },
        {
            "agent": "security",
            "rule_id": "SEC-002",
            "rule_source": "in-setup:06-security-policy.md#secrets-management",
            "file": "src/auth/login.ts",
            "line_start": 9,
            "line_end": 9,
            "severity": "high",
            "confidence": 0.95,
            "claim": "Password logged in plaintext — sensitive data exposure.",
            "evidence_quote": "    console.log(`Login attempt for ${email} with password ${password}`);",
            "why_it_matters": "Per 06-security-policy.md#secrets-management: secrets must never appear in log statements.",
            "suggestion": "console.log(`Login attempt for ${email}`);  // never log password",
            "false_positive_risk": "low",
            "false_positive_reason": None,
        },
        {
            "agent": "security",
            "rule_id": "SEC-001",
            "rule_source": "in-setup:06-security-policy.md#secrets-management",
            "file": "src/users/users.service.ts",
            "line_start": 4,
            "line_end": 4,
            "severity": "critical",
            "confidence": 0.99,
            "claim": "Hardcoded API key in source code.",
            "evidence_quote": "const API_KEY = 'sk-prod-1234567890abcdef';",
            "why_it_matters": "Per 06-security-policy.md#secrets-management: API keys must be in environment variables.",
            "suggestion": "const API_KEY = process.env.API_KEY;",
            "false_positive_risk": "low",
            "false_positive_reason": None,
        },
        {
            # Low confidence — should be silenced by Precision Gate
            "agent": "security",
            "rule_id": "SEC-005",
            "rule_source": "in-setup:06-security-policy.md#authentication",
            "file": "src/auth/login.ts",
            "line_start": 6,
            "line_end": 6,
            "severity": "high",
            "confidence": 0.55,  # < 0.80 → silenced
            "claim": "Possible missing auth decorator — needs investigation.",
            "evidence_quote": "  async login(email: string, password: string) {",
            "why_it_matters": "Auth endpoints require explicit auth decorators.",
            "suggestion": "Add @Public() or appropriate auth guard decorator.",
            "false_positive_risk": "high",
            "false_positive_reason": "Cannot confirm from diff alone whether auth is applied at module level.",
        },
    ]

    (agents_dir / "security.findings.json").write_text(
        json.dumps({"findings": findings}, indent=2), encoding="utf-8"
    )

    # Write a basic coverage matrix
    coverage = {
        "agent": "security",
        "run_id": "test-run",
        "rules_in_checklist_total": 12,
        "rules_evaluated_total": 12,
        "diff_files_total": 2,
        "files_in_domain_total": 2,
        "files_in_domain_evaluated": 2,
        "rules": [
            {
                "rule_id": f"SEC-{i:03d}",
                "title": f"Rule {i}",
                "source": "in-setup:06-security-policy.md#input-validation",
                "verdicts": [
                    {"file": "src/auth/login.ts", "verdict": "compliant"},
                    {"file": "src/users/users.service.ts", "verdict": "compliant"},
                ],
            }
            for i in range(1, 13)
        ],
    }
    # Override specific rules with violations
    for rule in coverage["rules"]:
        if rule["rule_id"] == "SEC-007":
            rule["verdicts"][0]["verdict"] = "violation"
        if rule["rule_id"] == "SEC-001":
            rule["verdicts"][1]["verdict"] = "violation"
        if rule["rule_id"] == "SEC-002":
            rule["verdicts"][0]["verdict"] = "violation"

    (agents_dir / "security.coverage.json").write_text(
        json.dumps(coverage, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_config_loads(setup_path: Path) -> None:
    config = load_config(setup_path)
    assert config.framework_name == "TRUST"
    assert config.mode == "strict"
    assert config.profile_type == "pilot"
    assert len(config.required_docs) == 7
    assert len([a for a in config.agents if a.enabled]) >= 1
    assert config.confidence_threshold == 0.80
    print("  ✓ config loads correctly")


def test_grounding_loads(setup_path: Path) -> None:
    config = load_config(setup_path)
    manifest = load_grounding(config, setup_path)
    ok, errors = validate_grounding_dod(manifest)
    assert ok, f"Grounding DoD failed: {errors}"
    assert len(manifest.docs) == 7
    assert manifest.total_bytes() >= 5000
    assert not manifest.missing_required
    print(f"  ✓ grounding loads: {len(manifest.docs)} docs, {manifest.total_bytes():,} bytes")


def test_halt_on_missing_grounding(tmp_dir: Path) -> None:
    """A missing required doc must trigger grounding DoD failure."""
    broken_setup = tmp_dir / "broken-setup"
    shutil.copytree(tmp_dir / "mock-setup", broken_setup)

    # Remove a required doc
    (broken_setup / "grounding" / "06-security-policy.md").unlink()

    config = load_config(broken_setup)
    manifest = load_grounding(config, broken_setup)
    ok, errors = validate_grounding_dod(manifest)

    assert not ok, "Should have failed: security policy is missing"
    assert any("06-security-policy" in e for e in errors + manifest.missing_required)
    print("  ✓ missing grounding doc correctly detected (would HALT)")


def test_precision_gate(run_dir: Path) -> None:
    """Findings with confidence < 0.80 must be silenced."""
    gate_file = run_dir / "gate.report.json"
    assert gate_file.exists(), "gate.report.json not found"

    gate = json.loads(gate_file.read_text())
    passed = gate["passed"]
    silenced = gate["silenced"]

    assert all(f["confidence"] >= 0.80 for f in passed), \
        "Some passed findings have confidence < 0.80"
    assert all(f["confidence"] < 0.80 for f in silenced), \
        "Some silenced findings have confidence >= 0.80"
    assert len(passed) == 3, f"Expected 3 passed findings, got {len(passed)}"
    assert len(silenced) == 1, f"Expected 1 silenced finding, got {len(silenced)}"
    print(f"  ✓ precision gate: {len(passed)} passed, {len(silenced)} silenced")


def test_meta_review(run_dir: Path) -> None:
    """evidence_quote must be literal in the diff."""
    meta_file = run_dir / "meta-review.json"
    assert meta_file.exists(), "meta-review.json not found"

    meta = json.loads(meta_file.read_text())
    validated = meta["validated"]
    hallucinations = meta["hallucinations_caught"]

    assert validated >= 1, "At least 1 finding should pass meta-review"
    print(f"  ✓ meta-review: {validated} validated, {hallucinations} hallucinations")


def test_review_md_generated(run_dir: Path) -> None:
    """REVIEW.md must exist and contain key sections."""
    review = run_dir / "REVIEW.md"
    assert review.exists(), "REVIEW.md not generated"

    content = review.read_text()
    assert "TRUST Review" in content
    assert "AI never approves or rejects" in content.replace("\n", " ")
    assert "SEC-007" in content or "SEC-001" in content
    assert "Summary" in content
    print("  ✓ REVIEW.md generated with correct structure")


def test_validate_coverage_script(run_dir: Path) -> None:
    """validate_coverage.py must return ok for a complete coverage matrix."""
    coverage_file = run_dir / "agents" / "security.coverage.json"
    assert coverage_file.exists()

    result = validate_coverage(coverage_file)
    assert result.ok, f"Coverage validation failed: {result.errors}"
    print(f"  ✓ coverage script: {result.summary}")


def test_run_manifest_complete(run_dir: Path) -> None:
    """run-manifest.json must exist and show the run status."""
    manifest_file = run_dir / "run-manifest.json"
    assert manifest_file.exists()

    manifest = json.loads(manifest_file.read_text())
    assert "run_id" in manifest
    assert "phases" in manifest
    assert len(manifest["phases"]) == 8
    print(f"  ✓ run-manifest: run_id={manifest['run_id']}, status={manifest['overall_status']}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_pipeline_phases(setup_path: Path, run_dir: Path) -> None:
    """Simulate the phases that would be driven by Claude after agent execution."""
    import sys
    sys.path.insert(0, str(REPO_ROOT))

    from core.orchestrator import (
        _run_phase_4_precision_gate,
        _run_phase_6_traceability_skip,
        _run_phase_7_output,
    )
    from core.config_loader import load_config
    from core.run_manifest import (
        mark_phase_start, mark_phase_done, mark_phase_skipped,
        finalise_manifest, save_manifest
    )
    from core.models import RunManifest, PhaseRecord, PhaseStatus
    import json

    config = load_config(setup_path)

    # Reload manifest
    manifest_data = json.loads((run_dir / "run-manifest.json").read_text())
    manifest = RunManifest(
        run_id=manifest_data["run_id"],
        branch=manifest_data["branch"],
        target_id=manifest_data["target_id"],
        diff_sha=manifest_data["diff_sha"],
        started_at=manifest_data["started_at"],
    )
    from core.run_manifest import PHASE_DEFINITIONS
    manifest.phases = [PhaseRecord(phase_id=pid, name=name) for pid, name in PHASE_DEFINITIONS]

    # Phase 4 — Precision Gate
    _run_phase_4_precision_gate(manifest, run_dir, config.confidence_threshold, run_dir / "agents")

    # Phase 5 — Meta-review (inline)
    phase5 = mark_phase_start(manifest, 5, run_dir)
    gate_data = json.loads((run_dir / "gate.report.json").read_text())
    passed_findings = gate_data.get("passed", [])
    diff_text = (run_dir / "diff.patch").read_text(encoding="utf-8")

    validated = []
    hallucinations = []
    for f in passed_findings:
        quote = f.get("evidence_quote", "")
        if quote and quote.strip() in diff_text:
            validated.append(f)
        else:
            f["rejection_reason"] = "evidence_quote not found literally in diff"
            hallucinations.append(f)

    meta_report = {
        "findings_in": len(passed_findings),
        "validated": len(validated),
        "hallucinations_caught": len(hallucinations),
        "findings": validated,
        "hallucinations_caught_detail": hallucinations,
    }
    (run_dir / "meta-review.json").write_text(json.dumps(meta_report, indent=2))
    gate_data["passed"] = validated
    (run_dir / "gate.report.json").write_text(json.dumps(gate_data, indent=2))
    mark_phase_done(manifest, phase5, run_dir, artifact="meta-review.json")

    # Phase 6 — Traceability skip
    _run_phase_6_traceability_skip(manifest, run_dir)

    # Phase 7 — Output
    output_path = run_dir / "REVIEW.md"
    _run_phase_7_output(manifest, run_dir, manifest.branch, output_path)

    finalise_manifest(manifest, run_dir)


def main() -> int:
    print("\n" + "="*60)
    print("TRUST MVP — End-to-End Test")
    print("="*60)

    passed = 0
    failed = 0

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        # Build mock setup
        setup_path = build_mock_setup(tmp_dir)
        print(f"\n📁 Mock setup: {setup_path}")

        # Create run dir
        runs_dir = setup_path / "runs"
        from core.run_manifest import create_manifest
        manifest, run_dir = create_manifest("feat/PAY-123", "mock-product", "mock-diff", runs_dir)
        print(f"📋 Run dir: {run_dir}\n")

        # Copy diff to run dir
        shutil.copy(MOCK_DIFF, run_dir / "diff.patch")

        # Simulate agent writing findings
        make_mock_findings(run_dir)

        # Run pipeline phases 4-7
        run_pipeline_phases(setup_path, run_dir)

        tests = [
            ("Config loads correctly", lambda: test_config_loads(setup_path)),
            ("Grounding loads + DoD passes", lambda: test_grounding_loads(setup_path)),
            ("Halt on missing grounding", lambda: test_halt_on_missing_grounding(tmp_dir)),
            ("Precision Gate filters correctly", lambda: test_precision_gate(run_dir)),
            ("Meta-review validates quotes", lambda: test_meta_review(run_dir)),
            ("REVIEW.md generated", lambda: test_review_md_generated(run_dir)),
            ("validate_coverage.py works", lambda: test_validate_coverage_script(run_dir)),
            ("run-manifest.json complete", lambda: test_run_manifest_complete(run_dir)),
        ]

        for name, test_fn in tests:
            print(f"  Testing: {name}")
            try:
                test_fn()
                passed += 1
            except Exception as e:
                print(f"  ✗ FAILED: {e}")
                failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
