"""Isolated tests for trust-security-review skill scripts.

These tests do NOT require the orchestrator, Claude Code, or a running TRUST
installation. All fixtures are inline or use the shared mock-grounding directory.

Run with:
    python -m pytest tests/skills/test_security_skill.py -v
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup — add the scripts directory to sys.path so we can import directly
# ---------------------------------------------------------------------------

SKILL_ROOT = Path(__file__).parent.parent.parent / "skills" / "trust-security-review"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
MOCK_GROUNDING_DIR = Path(__file__).parent.parent / "fixtures" / "mock-grounding"
MOCK_DIFF = Path(__file__).parent.parent / "fixtures" / "mock-diff" / "feat-PAY-123.patch"

sys.path.insert(0, str(SCRIPTS_DIR))

from parse_checklist import parse_checklist  # noqa: E402
from check_evidence_literal import check_evidence_quotes  # noqa: E402
from validate_coverage import validate_coverage  # noqa: E402
from check_rule_source import check_rule_sources  # noqa: E402
from validate_dod_attestation import validate_attestation  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tmp_json(tmp_path: Path, name: str, content) -> Path:
    """Write content as JSON to a temp file and return the path."""
    p = tmp_path / name
    p.write_text(json.dumps(content), encoding="utf-8")
    return p


MINIMAL_COVERAGE = {
    "agent": "security",
    "rules_in_checklist_total": 1,
    "rules_evaluated_total": 1,
    "diff_files_total": 1,
    "files_in_domain_total": 1,
    "files_in_domain_evaluated": 1,
    "rules": [
        {
            "rule_id": "SEC-001",
            "verdicts": [
                {"file": "src/auth/login.ts", "verdict": "compliant"}
            ],
        }
    ],
}

VALID_DOD = {
    "agent": "security",
    "agent_version": "1.0.0",
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-05-18T14:32:00Z",
    "dod": {
        "grounding": {
            "loaded": True,
            "docs_read": [{"path": "06-security-policy.md", "sha256": "abc", "sections_indexed": 8}],
            "missing_required": [],
        },
        "checklist": {
            "loaded": True,
            "rules_in_checklist_total": 12,
            "rules_with_valid_source": 12,
        },
        "coverage": {
            "diff_files_total": 2,
            "files_in_domain_total": 2,
            "files_in_domain_evaluated": 2,
            "files_in_domain_evaluated_pct": 100,
            "rules_evaluated_total": 12,
            "rules_evaluated_pct": 100,
            "coverage_matrix_complete": True,
            "not_applicable_with_justification_pct": 100,
        },
        "findings": {
            "emitted": 2,
            "every_finding_has_rule_id": True,
            "every_finding_has_rule_source": True,
            "every_finding_has_evidence_quote": True,
            "every_finding_has_confidence": True,
            "every_finding_confidence_gte_080": True,
            "every_evidence_quote_literal": True,
        },
        "self_check_passed": True,
        "halt_required": False,
    },
}

CHECKLIST_VALID_12 = textwrap.dedent("""\
    # Security Checklist
    ### SEC-001 — No hardcoded secrets in source code
    **Source:** `06-security-policy.md#secrets-management`
    **Severity default:** critical
    **Applies to:** all files

    ### SEC-002 — No secrets in log statements
    **Source:** `06-security-policy.md#secrets-management`
    **Severity default:** high
    **Applies to:** all files

    ### SEC-003 — Input validation on all external data
    **Source:** `06-security-policy.md#input-validation`
    **Severity default:** high
    **Applies to:** controller/handler/route files

    ### SEC-004 — Output encoding for user-facing content
    **Source:** `06-security-policy.md#output-encoding`
    **Severity default:** high
    **Applies to:** view/template/response files

    ### SEC-005 — Authentication required on non-public endpoints
    **Source:** `06-security-policy.md#authentication`
    **Severity default:** critical
    **Applies to:** controller/handler/route files

    ### SEC-006 — Authorization check before accessing resources
    **Source:** `06-security-policy.md#authorization`
    **Severity default:** critical
    **Applies to:** service/use-case/handler files

    ### SEC-007 — Parameterized queries for all database access
    **Source:** `06-security-policy.md#input-validation`
    **Severity default:** critical
    **Applies to:** all files with DB access

    ### SEC-008 — Approved cryptographic algorithms only
    **Source:** `06-security-policy.md#cryptography`
    **Severity default:** high
    **Applies to:** all files

    ### SEC-009 — HTTPS-only for external communication
    **Source:** `06-security-policy.md#network-security`
    **Severity default:** high
    **Applies to:** HTTP client files, configuration files

    ### SEC-010 — Dependency on patched versions
    **Source:** `06-security-policy.md#dependency-management`
    **Severity default:** medium
    **Applies to:** package.json, go.mod, requirements.txt

    ### SEC-011 — CORS policy explicitly configured
    **Source:** `06-security-policy.md#network-security`
    **Severity default:** medium
    **Applies to:** server/middleware configuration files

    ### SEC-012 — Error messages do not leak internal state
    **Source:** `06-security-policy.md#error-handling`
    **Severity default:** medium
    **Applies to:** error handler, middleware, API response files
""")


# ---------------------------------------------------------------------------
# parse_checklist tests
# ---------------------------------------------------------------------------


def test_parse_checklist_valid():
    """12 rules parsed from the valid checklist template."""
    rules, errors = parse_checklist(CHECKLIST_VALID_12)
    assert errors == [], f"Unexpected errors: {errors}"
    assert len(rules) == 12
    rule_ids = [r.rule_id for r in rules]
    assert "SEC-001" in rule_ids
    assert "SEC-012" in rule_ids


def test_parse_checklist_missing_source():
    """Rule without Source field triggers exit 1 (error returned)."""
    md = textwrap.dedent("""\
        ### SEC-001 — No hardcoded secrets in source code
        **Severity default:** critical
        **Applies to:** all files
    """)
    rules, errors = parse_checklist(md)
    assert len(errors) > 0
    assert any("source" in e.lower() or "Source" in e for e in errors)
    assert len(rules) == 0


def test_parse_checklist_bad_rule_id():
    """Rule with non-standard rule_id format is silently treated as non-rule header."""
    md = textwrap.dedent("""\
        ### SEC-01 — Bad format (only 2 digits)
        **Source:** `06-security-policy.md#secrets-management`
        **Severity default:** critical
        **Applies to:** all files
    """)
    # The regex requires SEC-XXX (3 digits), so SEC-01 won't match and produces 0 rules
    rules, errors = parse_checklist(md)
    assert len(rules) == 0


# ---------------------------------------------------------------------------
# check_evidence_literal tests
# ---------------------------------------------------------------------------


def test_check_evidence_literal_passes():
    """Quote present in diff → result.found = True."""
    diff = MOCK_DIFF.read_text(encoding="utf-8")
    findings = [
        {
            "rule_id": "SEC-007",
            "file": "src/auth/login.ts",
            "evidence_quote": "const user = await db.query(`SELECT * FROM users WHERE email='${email}'`);",
        }
    ]
    results = check_evidence_quotes(findings, diff)
    assert len(results) == 1
    assert results[0].found is True


def test_check_evidence_literal_fails():
    """Quote absent from diff → result.found = False."""
    diff = MOCK_DIFF.read_text(encoding="utf-8")
    findings = [
        {
            "rule_id": "SEC-007",
            "file": "src/auth/login.ts",
            "evidence_quote": "this exact string is not in the diff at all!!",
        }
    ]
    results = check_evidence_quotes(findings, diff)
    assert len(results) == 1
    assert results[0].found is False


def test_check_evidence_paraphrase_fails():
    """Paraphrased quote is NOT a substring → fails literal check."""
    diff = MOCK_DIFF.read_text(encoding="utf-8")
    # The real line uses template literals; a paraphrase with double quotes fails
    findings = [
        {
            "rule_id": "SEC-007",
            "file": "src/auth/login.ts",
            "evidence_quote": 'db.query("SELECT * FROM users WHERE email=" + email)',
        }
    ]
    results = check_evidence_quotes(findings, diff)
    assert results[0].found is False


# ---------------------------------------------------------------------------
# validate_coverage tests
# ---------------------------------------------------------------------------


def test_validate_coverage_100pct(tmp_path: Path):
    """Complete coverage matrix → ValidationResult.ok = True."""
    coverage_file = _tmp_json(tmp_path, "security.coverage.json", MINIMAL_COVERAGE)
    result = validate_coverage(coverage_file)
    assert result.ok is True
    assert result.errors == []


def test_validate_coverage_missing_rule(tmp_path: Path):
    """rules_evaluated_total < rules_in_checklist_total → ok = False."""
    data = dict(MINIMAL_COVERAGE)
    data["rules_evaluated_total"] = 0
    data["rules_in_checklist_total"] = 1
    data["rules"] = []
    coverage_file = _tmp_json(tmp_path, "security.coverage.json", data)
    result = validate_coverage(coverage_file)
    assert result.ok is False
    assert any("empty" in e.lower() or "missing" in e.lower() for e in result.errors)


def test_validate_coverage_na_no_reason(tmp_path: Path):
    """N/A verdict without justification → ok = False."""
    data = {
        **MINIMAL_COVERAGE,
        "rules": [
            {
                "rule_id": "SEC-001",
                "verdicts": [
                    {"file": "src/auth/login.ts", "verdict": "not_applicable", "reason": ""}
                ],
            }
        ],
    }
    coverage_file = _tmp_json(tmp_path, "security.coverage.json", data)
    result = validate_coverage(coverage_file)
    assert result.ok is False
    assert any("justification" in e.lower() or "N/A" in e for e in result.errors)


# ---------------------------------------------------------------------------
# check_rule_source tests
# ---------------------------------------------------------------------------


def test_check_rule_source_resolves():
    """Anchor present in grounding → resolves = True."""
    findings = [
        {
            "rule_id": "SEC-007",
            "file": "src/auth/login.ts",
            "rule_source": "in-setup:06-security-policy.md#input-validation",
        }
    ]
    results = check_rule_sources(findings, MOCK_GROUNDING_DIR)
    assert len(results) == 1
    assert results[0].resolves is True


def test_check_rule_source_missing_anchor():
    """Non-existent anchor → resolves = False with available_anchors listed."""
    findings = [
        {
            "rule_id": "SEC-999",
            "file": "src/auth/login.ts",
            "rule_source": "in-setup:06-security-policy.md#nonexistent-section-xyz",
        }
    ]
    results = check_rule_sources(findings, MOCK_GROUNDING_DIR)
    assert len(results) == 1
    assert results[0].resolves is False
    assert results[0].available_anchors is not None
    assert len(results[0].available_anchors) > 0


# ---------------------------------------------------------------------------
# validate_dod_attestation tests
# ---------------------------------------------------------------------------


def test_validate_dod_passes():
    """Complete valid attestation → no errors."""
    errors = validate_attestation(VALID_DOD)
    assert errors == [], f"Unexpected errors: {errors}"


def test_validate_dod_pct_not_100():
    """rules_evaluated_pct: 87 → error reported."""
    import copy
    data = copy.deepcopy(VALID_DOD)
    data["dod"]["coverage"]["rules_evaluated_pct"] = 87
    # Also need to make halt_required True and self_check_passed False to be consistent
    # but we're testing that 87 is caught before those checks
    errors = validate_attestation(data)
    assert any("rules_evaluated_pct" in e for e in errors)


def test_validate_dod_false_positive_field():
    """`every_evidence_quote_literal: false` → error reported."""
    import copy
    data = copy.deepcopy(VALID_DOD)
    data["dod"]["findings"]["every_evidence_quote_literal"] = False
    errors = validate_attestation(data)
    assert any("every_evidence_quote_literal" in e for e in errors)
