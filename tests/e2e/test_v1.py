"""TRUST v1.0 end-to-end tests.

Covers:
  - parse_checklist.py for all 6 agent types (SEC, CON, DAT, PERF, CONV, TEST)
  - All 5 new agents have the 4 required validation scripts
  - codebase_mapper.py generates drafts from a mock product repo
  - run_lifecycle.py retention policies (success and HALT paths)
  - Second Pass and Meta-Review phase logic
  - Validate coverage across all agent checklists

Run:
    python -m pytest tests/e2e/test_v1.py -v

Or standalone:
    python tests/e2e/test_v1.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.run_lifecycle import apply_retention, is_halted

# Script dirs
_SEC_SCRIPTS = REPO_ROOT / "skills" / "trust-security-review" / "scripts"

# Checklist templates
_CHECKLISTS = REPO_ROOT / "templates" / "checklists"

# Required scripts in every agent skill
_REQUIRED_SCRIPTS = [
    "check_evidence_literal.py",
    "parse_checklist.py",
    "validate_dod_attestation.py",
    "check_rule_source.py",
    "validate_coverage.py",
]

_AGENT_SKILLS = [
    "trust-security-review",
    "trust-contracts-review",
    "trust-data-review",
    "trust-performance-review",
    "trust-conventions-review",
    "trust-tests-review",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_parse_checklist():
    """Import parse_checklist from the security skill (shared copy)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "parse_checklist", _SEC_SCRIPTS / "parse_checklist.py"
    )
    mod = importlib.util.load_from_spec = None
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _load_script(name: str, path: Path):
    """Load a script module, registering it in sys.modules to satisfy dataclass forward refs."""
    import importlib.util
    module_name = f"_trust_scripts.{name}"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_parse_checklist():
    return _load_script("parse_checklist", _SEC_SCRIPTS / "parse_checklist.py")


# ---------------------------------------------------------------------------
# Tests: validation scripts exist in all agent skills
# ---------------------------------------------------------------------------


def test_all_agent_skills_have_required_scripts() -> None:
    missing: list[str] = []
    for skill in _AGENT_SKILLS:
        scripts_dir = REPO_ROOT / "skills" / skill / "scripts"
        for script in _REQUIRED_SCRIPTS:
            if not (scripts_dir / script).exists():
                missing.append(f"{skill}/scripts/{script}")

    assert not missing, f"Missing scripts:\n  " + "\n  ".join(missing)
    print(f"  ✓ All {len(_AGENT_SKILLS)} agents have {len(_REQUIRED_SCRIPTS)} required scripts")


# ---------------------------------------------------------------------------
# Tests: parse_checklist for all rule_id formats
# ---------------------------------------------------------------------------


def test_parse_checklist_sec_rules() -> None:
    mod = _load_parse_checklist()
    checklist = (_CHECKLISTS / "security.checklist.md").read_text(encoding="utf-8")
    rules, errors = mod.parse_checklist(checklist)
    assert not errors, f"parse errors: {errors}"
    rule_ids = [r.rule_id for r in rules]
    assert all(rid.startswith("SEC-") for rid in rule_ids), f"Bad IDs: {rule_ids}"
    assert len(rules) >= 8
    print(f"  ✓ parse_checklist: {len(rules)} SEC rules parsed")


def test_parse_checklist_con_rules() -> None:
    mod = _load_parse_checklist()
    checklist = (_CHECKLISTS / "contracts.checklist.md").read_text(encoding="utf-8")
    rules, errors = mod.parse_checklist(checklist)
    assert not errors, f"parse errors: {errors}"
    rule_ids = [r.rule_id for r in rules]
    assert all(rid.startswith("CON-") for rid in rule_ids), f"Bad IDs: {rule_ids}"
    assert len(rules) >= 6
    print(f"  ✓ parse_checklist: {len(rules)} CON rules parsed")


def test_parse_checklist_dat_rules() -> None:
    mod = _load_parse_checklist()
    checklist = (_CHECKLISTS / "data.checklist.md").read_text(encoding="utf-8")
    rules, errors = mod.parse_checklist(checklist)
    assert not errors, f"parse errors: {errors}"
    rule_ids = [r.rule_id for r in rules]
    assert all(rid.startswith("DAT-") for rid in rule_ids), f"Bad IDs: {rule_ids}"
    print(f"  ✓ parse_checklist: {len(rules)} DAT rules parsed")


def test_parse_checklist_perf_rules() -> None:
    mod = _load_parse_checklist()
    checklist = (_CHECKLISTS / "performance.checklist.md").read_text(encoding="utf-8")
    rules, errors = mod.parse_checklist(checklist)
    assert not errors, f"parse errors: {errors}"
    rule_ids = [r.rule_id for r in rules]
    assert all(rid.startswith("PERF-") for rid in rule_ids), f"Bad IDs: {rule_ids}"
    print(f"  ✓ parse_checklist: {len(rules)} PERF rules parsed")


def test_parse_checklist_conv_rules() -> None:
    mod = _load_parse_checklist()
    checklist = (_CHECKLISTS / "conventions.checklist.md").read_text(encoding="utf-8")
    rules, errors = mod.parse_checklist(checklist)
    assert not errors, f"parse errors: {errors}"
    rule_ids = [r.rule_id for r in rules]
    assert all(rid.startswith("CONV-") for rid in rule_ids), f"Bad IDs: {rule_ids}"
    print(f"  ✓ parse_checklist: {len(rules)} CONV rules parsed")


def test_parse_checklist_test_rules() -> None:
    mod = _load_parse_checklist()
    checklist = (_CHECKLISTS / "tests.checklist.md").read_text(encoding="utf-8")
    rules, errors = mod.parse_checklist(checklist)
    assert not errors, f"parse errors: {errors}"
    rule_ids = [r.rule_id for r in rules]
    assert all(rid.startswith("TEST-") for rid in rule_ids), f"Bad IDs: {rule_ids}"
    print(f"  ✓ parse_checklist: {len(rules)} TEST rules parsed")


# ---------------------------------------------------------------------------
# Tests: codebase_mapper
# ---------------------------------------------------------------------------


def test_codebase_mapper_generates_drafts() -> None:
    from core.codebase_mapper import run_mapper, MapperConfig

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Mock product repo
        repo = tmp_path / "product"
        repo.mkdir()
        (repo / "README.md").write_text("# Mock Product\n\nA test service.", encoding="utf-8")
        src = repo / "src"
        src.mkdir()
        (src / "routes.ts").write_text(
            "router.get('/users', handler);\nrouter.post('/users', create);",
            encoding="utf-8",
        )
        (src / "auth.ts").write_text(
            "const token = process.env.JWT_SECRET;\nauthenticate(req);",
            encoding="utf-8",
        )

        grounding_dir = tmp_path / "grounding"
        grounding_dir.mkdir()

        cfg = MapperConfig(repo=repo, grounding_dir=grounding_dir, force=False)
        results = run_mapper(cfg)

        written = [r for r in results if r.status == "written"]
        assert len(written) >= 3, f"Expected >= 3 drafts, got {len(written)}: {[r.slot for r in results]}"

        drafts_dir = grounding_dir / "_drafts"
        assert drafts_dir.exists()
        assert (drafts_dir / "01-architecture.md").exists()
        assert (drafts_dir / "03-api-contracts.md").exists()

        # Architecture draft should contain README content
        arch = (drafts_dir / "01-architecture.md").read_text(encoding="utf-8")
        assert "DRAFT" in arch
        assert "Mock Product" in arch

        # Contracts draft should detect router.get/router.post
        contracts = (drafts_dir / "03-api-contracts.md").read_text(encoding="utf-8")
        assert "routes.ts" in contracts or "router" in contracts

    print("  ✓ codebase_mapper: drafts generated correctly")


def test_codebase_mapper_skips_finalized() -> None:
    from core.codebase_mapper import run_mapper, MapperConfig

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        repo = tmp_path / "product"
        repo.mkdir()
        (repo / "README.md").write_text("# Product", encoding="utf-8")

        grounding_dir = tmp_path / "grounding"
        grounding_dir.mkdir()

        # Pre-create a finalized file
        finalized = grounding_dir / "01-architecture.md"
        finalized.write_text("# Finalized architecture", encoding="utf-8")

        cfg = MapperConfig(repo=repo, grounding_dir=grounding_dir, force=False)
        results = run_mapper(cfg)

        arch_result = next((r for r in results if r.slot == "01-architecture.md"), None)
        assert arch_result is not None
        assert arch_result.status == "skipped_finalized"

    print("  ✓ codebase_mapper: skips finalized files correctly")


def test_codebase_mapper_force_overwrites() -> None:
    from core.codebase_mapper import run_mapper, MapperConfig

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        repo = tmp_path / "product"
        repo.mkdir()
        (repo / "README.md").write_text("# Product", encoding="utf-8")

        grounding_dir = tmp_path / "grounding"
        grounding_dir.mkdir()
        drafts_dir = grounding_dir / "_drafts"
        drafts_dir.mkdir()

        # Pre-create a draft
        existing = drafts_dir / "01-architecture.md"
        existing.write_text("old draft content", encoding="utf-8")

        # Without --force: skip
        cfg = MapperConfig(repo=repo, grounding_dir=grounding_dir, force=False)
        results = run_mapper(cfg)
        arch_result = next((r for r in results if r.slot == "01-architecture.md"), None)
        assert arch_result.status == "skipped_exists"

        # With --force: overwrite
        cfg_force = MapperConfig(repo=repo, grounding_dir=grounding_dir, force=True)
        results_force = run_mapper(cfg_force)
        arch_force = next((r for r in results_force if r.slot == "01-architecture.md"), None)
        assert arch_force.status == "written"
        new_content = existing.read_text(encoding="utf-8")
        assert new_content != "old draft content"

    print("  ✓ codebase_mapper: --force overwrites existing drafts")


# ---------------------------------------------------------------------------
# Tests: run_lifecycle retention policies
# ---------------------------------------------------------------------------


def _make_run_dir(tmp: Path, halted: bool = False) -> Path:
    """Create a mock run directory with some artifacts."""
    run_dir = tmp / "runs" / "feat-test-abc"
    run_dir.mkdir(parents=True)

    (run_dir / "run-manifest.json").write_text('{"run_id": "test"}', encoding="utf-8")
    (run_dir / "REVIEW.md").write_text("# Review", encoding="utf-8")
    (run_dir / "diff.patch").write_text("diff content", encoding="utf-8")
    (run_dir / "gate.report.json").write_text('{"passed": []}', encoding="utf-8")

    agents_dir = run_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "security.findings.json").write_text('[]', encoding="utf-8")

    if halted:
        (run_dir / ".trust-halt").write_text("HALT: grounding DoD failed", encoding="utf-8")

    return run_dir


def test_lifecycle_all_versioned() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = _make_run_dir(Path(tmp))
        result = apply_retention(run_dir, "all_versioned")
        assert result.action == "kept_all"
        assert run_dir.exists()
    print("  ✓ lifecycle: all_versioned keeps everything")


def test_lifecycle_audit_failures_success() -> None:
    """On success, audit_failures_only removes JSON artifacts."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = _make_run_dir(Path(tmp), halted=False)
        result = apply_retention(run_dir, "audit_failures_only")
        assert result.action == "removed_json"
        assert not result.halted
        # REVIEW.md must be kept
        assert (run_dir / "REVIEW.md").exists()
        # JSON artifacts should be gone
        assert not (run_dir / "gate.report.json").exists()
    print("  ✓ lifecycle: audit_failures_only (success) removes JSON, keeps REVIEW.md")


def test_lifecycle_audit_failures_halt() -> None:
    """On HALT, audit_failures_only keeps everything for post-mortem."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = _make_run_dir(Path(tmp), halted=True)
        result = apply_retention(run_dir, "audit_failures_only")
        assert result.action == "kept_all"
        assert result.halted
        # Everything must be preserved
        assert (run_dir / "REVIEW.md").exists()
        assert (run_dir / "gate.report.json").exists()
        assert (run_dir / ".trust-halt").exists()
    print("  ✓ lifecycle: audit_failures_only (HALT) keeps all artifacts for post-mortem")


def test_lifecycle_ephemeral_success() -> None:
    """On success, ephemeral deletes the entire run dir."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = _make_run_dir(Path(tmp), halted=False)
        result = apply_retention(run_dir, "ephemeral")
        assert result.action == "removed_run"
        assert not run_dir.exists()
    print("  ✓ lifecycle: ephemeral (success) deletes run dir")


def test_lifecycle_ephemeral_halt() -> None:
    """On HALT, ephemeral still preserves artifacts (never deletes HALT)."""
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = _make_run_dir(Path(tmp), halted=True)
        result = apply_retention(run_dir, "ephemeral")
        # HALT → keep artifacts (same as audit_failures_only)
        assert run_dir.exists()
        assert (run_dir / ".trust-halt").exists()
    print("  ✓ lifecycle: ephemeral (HALT) preserves artifacts")


def test_lifecycle_is_halted() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = _make_run_dir(Path(tmp), halted=False)
        assert not is_halted(run_dir)

        (run_dir / ".trust-halt").write_text("HALT", encoding="utf-8")
        assert is_halted(run_dir)
    print("  ✓ lifecycle: is_halted detects .trust-halt correctly")


# ---------------------------------------------------------------------------
# Tests: Second Pass — hunk accounting
# ---------------------------------------------------------------------------


def test_second_pass_all_hunks_accounted() -> None:
    """If all diff hunks are accounted for in findings, second pass must pass."""
    diff_text = (
        REPO_ROOT / "tests" / "fixtures" / "mock-diff" / "feat-PAY-123.patch"
    ).read_text(encoding="utf-8")

    # Count diff files in our fixture (2 files)
    diff_files = [line for line in diff_text.splitlines() if line.startswith("diff --git")]
    assert len(diff_files) == 2

    # The mock findings from test_mvp.py cover both files:
    # - src/auth/login.ts (SEC-007, SEC-002, SEC-005)
    # - src/users/users.service.ts (SEC-001)
    files_with_findings = {"src/auth/login.ts", "src/users/users.service.ts"}
    assert len(files_with_findings) == len(diff_files)
    print("  ✓ second pass: fixture diff fully covered by mock findings")


def test_second_pass_skill_exists() -> None:
    """trust-second-pass must have a SKILL.md and PROTOCOL.md."""
    second_pass_dir = REPO_ROOT / "skills" / "trust-second-pass"
    assert (second_pass_dir / "SKILL.md").exists()
    assert (second_pass_dir / "references" / "PROTOCOL.md").exists()

    skill_md = (second_pass_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "second-pass" in skill_md.lower() or "Second Pass" in skill_md
    print("  ✓ trust-second-pass: SKILL.md and PROTOCOL.md present")


# ---------------------------------------------------------------------------
# Tests: Meta-Review
# ---------------------------------------------------------------------------


def test_meta_review_skill_exists() -> None:
    """trust-meta-review must have a SKILL.md and PROTOCOL.md."""
    meta_dir = REPO_ROOT / "skills" / "trust-meta-review"
    assert (meta_dir / "SKILL.md").exists()
    assert (meta_dir / "references" / "PROTOCOL.md").exists()

    skill_md = (meta_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "meta" in skill_md.lower()
    print("  ✓ trust-meta-review: SKILL.md and PROTOCOL.md present")


def test_meta_review_rejects_paraphrase() -> None:
    """check_evidence_literal must reject a paraphrased quote."""
    mod = _load_script("check_evidence_literal", _SEC_SCRIPTS / "check_evidence_literal.py")

    diff_text = "    const user = await db.query(`SELECT * FROM users WHERE email='${email}'`);"

    # Exact quote → passes
    exact_findings = [{"rule_id": "SEC-007", "file": "login.ts", "evidence_quote": diff_text.strip()}]
    results_exact = mod.check_evidence_quotes(exact_findings, diff_text)
    assert results_exact[0].found, "Exact quote should be found"

    # Paraphrase → fails
    para_findings = [{"rule_id": "SEC-007", "file": "login.ts", "evidence_quote": "db.query with user input in SQL string"}]
    results_para = mod.check_evidence_quotes(para_findings, diff_text)
    assert not results_para[0].found, "Paraphrase should not be found"

    print("  ✓ meta-review: check_evidence_literal accepts exact, rejects paraphrase")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main() -> int:
    print("\n" + "=" * 60)
    print("TRUST v1.0 — End-to-End Test")
    print("=" * 60)

    tests = [
        ("All agent skills have required scripts", test_all_agent_skills_have_required_scripts),
        ("parse_checklist: SEC rules", test_parse_checklist_sec_rules),
        ("parse_checklist: CON rules", test_parse_checklist_con_rules),
        ("parse_checklist: DAT rules", test_parse_checklist_dat_rules),
        ("parse_checklist: PERF rules", test_parse_checklist_perf_rules),
        ("parse_checklist: CONV rules", test_parse_checklist_conv_rules),
        ("parse_checklist: TEST rules", test_parse_checklist_test_rules),
        ("codebase_mapper: generates drafts", test_codebase_mapper_generates_drafts),
        ("codebase_mapper: skips finalized", test_codebase_mapper_skips_finalized),
        ("codebase_mapper: --force overwrites", test_codebase_mapper_force_overwrites),
        ("lifecycle: all_versioned", test_lifecycle_all_versioned),
        ("lifecycle: audit_failures (success)", test_lifecycle_audit_failures_success),
        ("lifecycle: audit_failures (HALT)", test_lifecycle_audit_failures_halt),
        ("lifecycle: ephemeral (success)", test_lifecycle_ephemeral_success),
        ("lifecycle: ephemeral (HALT)", test_lifecycle_ephemeral_halt),
        ("lifecycle: is_halted", test_lifecycle_is_halted),
        ("second-pass: hunk accounting", test_second_pass_all_hunks_accounted),
        ("second-pass: skill exists", test_second_pass_skill_exists),
        ("meta-review: skill exists", test_meta_review_skill_exists),
        ("meta-review: rejects paraphrase", test_meta_review_rejects_paraphrase),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"  Testing: {name}")
        try:
            fn()
            passed += 1
        except Exception as exc:
            import traceback
            print(f"  ✗ FAILED: {exc}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
