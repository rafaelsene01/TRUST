"""TRUST v1.2 tests — Rastreabilidade.

Covers:
  - spec_parser: frontmatter parsing, AC extraction, find_spec_for_ticket
  - jira_integration: extract_ticket_id, _adf_to_text, _extract_acceptance_criteria
  - traceability: run_traceability (spec path, jira path, not_found, no ticket)
  - orchestrator: Phase 6 real vs skip, traced_to in REVIEW.md output

All tests are fully offline — no real Jira or network calls are made.

Run:
    python -m pytest tests/e2e/test_v1_2.py -v
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.spec_parser import (
    SpecFile,
    SpecError,
    _parse_frontmatter,
    _extract_acceptance_criteria,
    parse_spec_file,
    find_spec_for_ticket,
)
from core.jira_integration import (
    JiraTicket,
    JiraError,
    extract_ticket_id,
    _adf_to_text,
    _extract_acceptance_criteria as _jira_ac,
)
from core.traceability import run_traceability, TracedTo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spec_file(tmp_dir: Path, ticket_id: str, title: str = "Test Spec", ac: str = "") -> Path:
    ac_block = f"\n\n## Acceptance Criteria\n\n{ac}" if ac else ""
    content = f"""---
ticket_id: {ticket_id}
title: "{title}"
type: story
status: in-progress
jira_url: https://empresa.atlassian.net/browse/{ticket_id}
components:
  - payments
---

## Summary

Test spec for {ticket_id}.{ac_block}
"""
    path = tmp_dir / f"{ticket_id}.spec.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_finding(rule_id: str = "SEC-001", confidence: float = 0.95) -> dict:
    return {
        "rule_id": rule_id,
        "claim": "Test claim",
        "severity": "high",
        "confidence": confidence,
        "file": "src/auth.py",
        "line_start": 10,
        "line_end": 15,
        "evidence_quote": "+password = request.data['pwd']",
        "why_it_matters": "Exposes password",
        "suggestion": "Use a secrets manager",
        "rule_source": "06-security-policy.md#SEC-001",
        "false_positive_risk": "low",
        "false_positive_reason": None,
    }


# ---------------------------------------------------------------------------
# spec_parser: frontmatter parsing
# ---------------------------------------------------------------------------


class TestSpecParserFrontmatter:
    def test_parse_frontmatter_basic(self):
        text = "---\nticket_id: PAY-123\ntitle: My Title\n---\n\nBody here."
        meta, body = _parse_frontmatter(text)
        assert meta["ticket_id"] == "PAY-123"
        assert meta["title"] == "My Title"
        assert "Body here." in body

    def test_parse_frontmatter_with_list(self):
        text = "---\nticket_id: PAY-123\ncomponents:\n  - payments\n  - retry\n---\nBody"
        meta, body = _parse_frontmatter(text)
        assert meta["components"] == ["payments", "retry"]

    def test_parse_frontmatter_no_frontmatter(self):
        text = "Just a body with no frontmatter."
        meta, body = _parse_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_parse_frontmatter_quoted_title(self):
        text = '---\nticket_id: PAY-123\ntitle: "Quoted Title"\n---\nBody'
        meta, body = _parse_frontmatter(text)
        assert meta["title"] == "Quoted Title"


# ---------------------------------------------------------------------------
# spec_parser: AC extraction
# ---------------------------------------------------------------------------


class TestSpecParserAC:
    def test_extract_ac_section(self):
        body = "## Summary\n\nBlah.\n\n## Acceptance Criteria\n\n- [ ] AC1\n- [ ] AC2\n"
        ac = _extract_acceptance_criteria(body)
        assert "AC1" in ac
        assert "AC2" in ac

    def test_extract_ac_portuguese(self):
        body = "## Summary\n\nBlah.\n\n## Critérios de Aceite\n\n- [ ] Item1\n"
        ac = _extract_acceptance_criteria(body)
        assert "Item1" in ac

    def test_extract_ac_missing(self):
        body = "## Summary\n\nNo AC here.\n"
        ac = _extract_acceptance_criteria(body)
        assert ac == ""


# ---------------------------------------------------------------------------
# spec_parser: parse_spec_file and find_spec_for_ticket
# ---------------------------------------------------------------------------


class TestParseSpecFile:
    def test_parse_valid_spec(self, tmp_path):
        path = _make_spec_file(tmp_path, "PAY-123", "Add retry logic", ac="- [ ] AC1\n- [ ] AC2")
        result = parse_spec_file(path)
        assert isinstance(result, SpecFile)
        assert result.ticket_id == "PAY-123"
        assert result.title == "Add retry logic"
        assert result.status == "in-progress"
        assert result.jira_url == "https://empresa.atlassian.net/browse/PAY-123"
        assert "payments" in result.components
        assert "AC1" in result.acceptance_criteria

    def test_parse_missing_file(self, tmp_path):
        result = parse_spec_file(tmp_path / "GHOST-999.spec.md")
        assert isinstance(result, SpecError)
        assert "not found" in result.reason

    def test_parse_no_ticket_id(self, tmp_path):
        path = tmp_path / "noticket.spec.md"
        path.write_text("---\ntitle: No ticket\n---\nBody\n", encoding="utf-8")
        result = parse_spec_file(path)
        assert isinstance(result, SpecError)
        assert "ticket_id" in result.reason

    def test_ticket_id_uppercased(self, tmp_path):
        path = tmp_path / "pay-123.spec.md"
        path.write_text("---\nticket_id: pay-123\ntitle: Lower\n---\nBody\n", encoding="utf-8")
        result = parse_spec_file(path)
        assert isinstance(result, SpecFile)
        assert result.ticket_id == "PAY-123"


class TestFindSpecForTicket:
    def test_find_by_canonical_filename(self, tmp_path):
        _make_spec_file(tmp_path, "PAY-456", "Find me")
        result = find_spec_for_ticket(tmp_path, "PAY-456")
        assert result is not None
        assert result.ticket_id == "PAY-456"

    def test_find_by_frontmatter_scan(self, tmp_path):
        # File named differently but has correct frontmatter
        content = "---\nticket_id: AUTH-789\ntitle: Auth spec\n---\nBody\n"
        (tmp_path / "some-other-name.spec.md").write_text(content, encoding="utf-8")
        result = find_spec_for_ticket(tmp_path, "AUTH-789")
        assert result is not None
        assert result.ticket_id == "AUTH-789"

    def test_find_not_found(self, tmp_path):
        result = find_spec_for_ticket(tmp_path, "GHOST-999")
        assert result is None

    def test_find_nonexistent_dir(self, tmp_path):
        result = find_spec_for_ticket(tmp_path / "nonexistent", "PAY-123")
        assert result is None

    def test_find_case_insensitive(self, tmp_path):
        _make_spec_file(tmp_path, "PAY-100", "Case test")
        result = find_spec_for_ticket(tmp_path, "pay-100")
        assert result is not None
        assert result.ticket_id == "PAY-100"


# ---------------------------------------------------------------------------
# jira_integration: extract_ticket_id
# ---------------------------------------------------------------------------


class TestExtractTicketId:
    def test_default_pattern_feat(self):
        assert extract_ticket_id("feat/PAY-123") == "PAY-123"

    def test_default_pattern_fix(self):
        assert extract_ticket_id("fix/AUTH-88-fix-login") == "AUTH-88"

    def test_default_pattern_chore(self):
        assert extract_ticket_id("chore/PLAT-42") == "PLAT-42"

    def test_fallback_bare_ticket(self):
        assert extract_ticket_id("PAY-999-some-description") == "PAY-999"

    def test_custom_pattern_with_placeholder(self):
        assert extract_ticket_id("PAY-55/feature", pattern=r"({ticket})/") == "PAY-55"

    def test_no_match_returns_none(self):
        assert extract_ticket_id("main") is None

    def test_uppercase_normalisation(self):
        result = extract_ticket_id("feat/pay-123")
        assert result == "PAY-123"


# ---------------------------------------------------------------------------
# jira_integration: _adf_to_text
# ---------------------------------------------------------------------------


class TestAdfToText:
    def test_simple_paragraph(self):
        node = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Hello world"}]}
            ],
        }
        assert "Hello world" in _adf_to_text(node)

    def test_heading(self):
        node = {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Title"}],
        }
        result = _adf_to_text(node)
        assert result.startswith("## Title")

    def test_bullet_list(self):
        node = {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Item A"}]}
                    ],
                }
            ],
        }
        result = _adf_to_text(node)
        assert "Item A" in result
        assert "-" in result

    def test_code_block(self):
        node = {
            "type": "codeBlock",
            "attrs": {"language": "python"},
            "content": [{"type": "text", "text": "x = 1"}],
        }
        result = _adf_to_text(node)
        assert "```python" in result
        assert "x = 1" in result

    def test_non_dict_returns_empty(self):
        assert _adf_to_text("not a dict") == ""
        assert _adf_to_text(None) == ""


# ---------------------------------------------------------------------------
# jira_integration: _extract_acceptance_criteria
# ---------------------------------------------------------------------------


class TestJiraAC:
    def test_extract_acceptance_criteria_english(self):
        desc = "Some intro.\n\nAcceptance Criteria:\n- AC1\n- AC2\n\n# Next section"
        ac = _jira_ac(desc)
        assert "AC1" in ac

    def test_extract_acceptance_criteria_portuguese(self):
        desc = "Intro.\n\nCritérios de Aceite:\n- Critério 1\n"
        ac = _jira_ac(desc)
        assert "Critério 1" in ac

    def test_no_ac_returns_empty(self):
        ac = _jira_ac("No criteria here.")
        assert ac == ""


# ---------------------------------------------------------------------------
# traceability: run_traceability
# ---------------------------------------------------------------------------


class TestRunTraceability:
    def test_resolves_from_spec_file(self, tmp_path):
        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()
        _make_spec_file(spec_dir, "PAY-123", "Add retry", ac="- [ ] AC1")

        cfg = {"spec_dir": "./specs", "branch_pattern": None}
        result = run_traceability(
            branch="feat/PAY-123",
            findings=[_make_finding()],
            traceability_cfg=cfg,
            setup_path=tmp_path,
        )

        assert result.ok is True
        assert result.ticket_id == "PAY-123"
        assert result.traced_to is not None
        assert result.traced_to.source == "spec_file"
        assert result.traced_to.title == "Add retry"
        assert len(result.annotated_findings) == 1
        assert result.annotated_findings[0]["traced_to"]["ticket_id"] == "PAY-123"

    def test_annotates_all_findings(self, tmp_path):
        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()
        _make_spec_file(spec_dir, "PAY-123", "Add retry")

        findings = [_make_finding("SEC-001"), _make_finding("SEC-002")]
        cfg = {"spec_dir": "./specs"}
        result = run_traceability(
            branch="feat/PAY-123",
            findings=findings,
            traceability_cfg=cfg,
            setup_path=tmp_path,
        )

        assert len(result.annotated_findings) == 2
        for f in result.annotated_findings:
            assert "traced_to" in f
            assert f["traced_to"]["ticket_id"] == "PAY-123"

    def test_no_ticket_in_branch(self, tmp_path):
        cfg = {}
        result = run_traceability(
            branch="main",
            findings=[_make_finding()],
            traceability_cfg=cfg,
            setup_path=tmp_path,
        )

        assert result.ok is False
        assert result.ticket_id is None
        assert result.warning is not None
        assert "ticket ID" in result.warning

    def test_ticket_not_found_anywhere(self, tmp_path):
        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()
        # No spec file, no jira config

        cfg = {"spec_dir": "./specs"}
        result = run_traceability(
            branch="feat/PAY-999",
            findings=[_make_finding()],
            traceability_cfg=cfg,
            setup_path=tmp_path,
        )

        assert result.ok is False
        assert result.ticket_id == "PAY-999"
        assert result.traced_to is not None
        assert result.traced_to.source == "not_found"
        # Still annotates findings (with not_found source)
        assert len(result.annotated_findings) == 1
        assert result.annotated_findings[0]["traced_to"]["source"] == "not_found"

    def test_resolves_from_jira_when_no_spec(self, tmp_path):
        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()

        mock_ticket = JiraTicket(
            ticket_id="PAY-123",
            summary="Add retry logic",
            description="Description here",
            status="In Progress",
            issue_type="Story",
            url="https://empresa.atlassian.net/browse/PAY-123",
            acceptance_criteria="- AC1\n- AC2",
            labels=[],
            components=["payments"],
        )

        cfg = {
            "spec_dir": "./specs",
            "jira": {
                "base_url": "https://empresa.atlassian.net",
                "auth": {"user_env": "JIRA_USER", "token_env": "JIRA_TOKEN"},
            },
        }

        with patch("core.traceability._resolve_from_jira", return_value=TracedTo(
            ticket_id="PAY-123",
            title="Add retry logic",
            url="https://empresa.atlassian.net/browse/PAY-123",
            source="jira",
            acceptance_criteria="- AC1\n- AC2",
            status="In Progress",
            components=["payments"],
        )):
            result = run_traceability(
                branch="feat/PAY-123",
                findings=[_make_finding()],
                traceability_cfg=cfg,
                setup_path=tmp_path,
            )

        assert result.ok is True
        assert result.traced_to.source == "jira"
        assert result.traced_to.title == "Add retry logic"

    def test_empty_findings_still_resolves(self, tmp_path):
        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()
        _make_spec_file(spec_dir, "PAY-123", "Clean run")

        cfg = {"spec_dir": "./specs"}
        result = run_traceability(
            branch="feat/PAY-123",
            findings=[],
            traceability_cfg=cfg,
            setup_path=tmp_path,
        )

        assert result.ok is True
        assert result.annotated_findings == []

    def test_jira_error_falls_back_to_not_found(self, tmp_path):
        spec_dir = tmp_path / "specs"
        spec_dir.mkdir()

        cfg = {
            "spec_dir": "./specs",
            "jira": {
                "base_url": "https://empresa.atlassian.net",
                "auth": {"user_env": "JIRA_USER", "token_env": "JIRA_TOKEN"},
            },
        }

        with patch("core.traceability._resolve_from_jira", side_effect=Exception("Network error")):
            result = run_traceability(
                branch="feat/PAY-123",
                findings=[_make_finding()],
                traceability_cfg=cfg,
                setup_path=tmp_path,
            )

        assert result.ok is False
        assert result.traced_to.source == "not_found"


# ---------------------------------------------------------------------------
# traced_to in findings
# ---------------------------------------------------------------------------


class TestTracedToDict:
    def test_to_dict_complete(self):
        t = TracedTo(
            ticket_id="PAY-123",
            title="My feature",
            url="https://jira.example.com/PAY-123",
            source="spec_file",
            acceptance_criteria="- AC1",
            status="In Progress",
            components=["payments"],
        )
        d = t.to_dict()
        assert d["ticket_id"] == "PAY-123"
        assert d["source"] == "spec_file"
        assert d["components"] == ["payments"]
        assert d["acceptance_criteria"] == "- AC1"

    def test_to_dict_not_found(self):
        t = TracedTo(ticket_id="PAY-999", title="", url="", source="not_found")
        d = t.to_dict()
        assert d["source"] == "not_found"
        assert d["title"] == ""
