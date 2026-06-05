"""TRUST v2.4 tests — GitHub-Native Integration.

Covers:
  - github_integration: extract_issue_number (patterns)
  - github_integration: GitHubClient.get_issue (mock subprocess)
  - github_integration: GitHubClient.health_check (mock subprocess)
  - traceability: _resolve_from_github (mock GitHubClient)
  - traceability: run_traceability with GitHub source
  - orchestrator: _post_github_pr_comment (mock subprocess)

All tests are fully offline — no real calls to GitHub.

Run:
    python -m pytest tests/e2e/test_v2_4.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.github_integration import (
    GitHubClient,
    GitHubError,
    GitHubIssue,
    extract_issue_number,
)
from core.traceability import TracedTo, _resolve_from_github


# ---------------------------------------------------------------------------
# Grupo 1 — extract_issue_number
# ---------------------------------------------------------------------------


class TestExtractIssueNumber:
    def test_extract_issue_number_feat_plain(self):
        """feat/152 → 152"""
        result = extract_issue_number("feat/152")
        assert result == 152

    def test_extract_issue_number_feat_with_desc(self):
        """feat/256-minha-feature → 256"""
        result = extract_issue_number("feat/256-minha-feature")
        assert result == 256

    def test_extract_issue_number_hash_prefix(self):
        """fix/#123 → 123 (via fallback pattern)"""
        result = extract_issue_number("fix/#123")
        assert result == 123

    def test_extract_issue_number_no_match(self):
        """no-issue → None"""
        result = extract_issue_number("no-issue")
        assert result is None


# ---------------------------------------------------------------------------
# Grupo 2 — GitHubClient.get_issue
# ---------------------------------------------------------------------------


class TestGitHubClientGetIssue:
    def _make_valid_issue_json(self) -> str:
        return json.dumps({
            "number": 152,
            "title": "Add OAuth",
            "body": "## AC\n- login works",
            "state": "open",
            "labels": [{"name": "feature"}],
            "url": "https://github.com/o/r/issues/152",
            "milestone": {"title": "v2"},
        })

    def test_github_client_get_issue_parses_json(self):
        """Mock subprocess returning valid JSON → GitHubIssue com campos corretos."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = self._make_valid_issue_json()
        mock_result.stderr = ""

        with patch("core.github_integration.subprocess.run", return_value=mock_result):
            client = GitHubClient()
            issue = client.get_issue(152)

        assert isinstance(issue, GitHubIssue)
        assert issue.issue_number == 152
        assert issue.title == "Add OAuth"
        assert issue.labels == ["feature"]
        assert issue.milestone == "v2"

    def test_github_client_get_issue_parses_body(self):
        """Verifica que body e url são capturados corretamente."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = self._make_valid_issue_json()
        mock_result.stderr = ""

        with patch("core.github_integration.subprocess.run", return_value=mock_result):
            client = GitHubClient()
            issue = client.get_issue(152)

        assert isinstance(issue, GitHubIssue)
        assert issue.body == "## AC\n- login works"
        assert issue.url == "https://github.com/o/r/issues/152"
        assert issue.state == "open"

    def test_github_client_get_issue_returns_error_on_failure(self):
        """Mock subprocess returncode=1 com stderr → retorna GitHubError."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "not found"

        with patch("core.github_integration.subprocess.run", return_value=mock_result):
            client = GitHubClient()
            result = client.get_issue(999)

        assert isinstance(result, GitHubError)
        assert result.reason == "not found"

    def test_github_client_get_issue_file_not_found(self):
        """Mock subprocess levantando FileNotFoundError → retorna GitHubError."""
        with patch(
            "core.github_integration.subprocess.run",
            side_effect=FileNotFoundError("gh not found"),
        ):
            client = GitHubClient()
            result = client.get_issue(152)

        assert isinstance(result, GitHubError)
        assert "gh" in result.reason.lower() or "cli" in result.reason.lower()

    def test_github_client_get_issue_with_repo_param(self):
        """Quando repo está configurado, passa --repo no comando."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = self._make_valid_issue_json()
        mock_result.stderr = ""

        with patch("core.github_integration.subprocess.run", return_value=mock_result) as mock_run:
            client = GitHubClient(repo="myorg/myrepo")
            client.get_issue(152)

        called_cmd = mock_run.call_args[0][0]
        assert "--repo" in called_cmd
        assert "myorg/myrepo" in called_cmd

    def test_github_client_get_issue_milestone_none(self):
        """Quando milestone é null no JSON, milestone retorna string vazia."""
        payload = json.dumps({
            "number": 10,
            "title": "No milestone",
            "body": "",
            "state": "open",
            "labels": [],
            "url": "https://github.com/o/r/issues/10",
            "milestone": None,
        })
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = payload
        mock_result.stderr = ""

        with patch("core.github_integration.subprocess.run", return_value=mock_result):
            client = GitHubClient()
            issue = client.get_issue(10)

        assert isinstance(issue, GitHubIssue)
        assert issue.milestone == ""


# ---------------------------------------------------------------------------
# Grupo 3 — GitHubClient.health_check
# ---------------------------------------------------------------------------


class TestGitHubClientHealthCheck:
    def test_github_client_health_check_ok(self):
        """Mock subprocess returncode=0 → (True, None)."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("core.github_integration.subprocess.run", return_value=mock_result):
            client = GitHubClient()
            ok, msg = client.health_check()

        assert ok is True
        assert msg is None

    def test_github_client_health_check_not_authed(self):
        """Mock subprocess returncode=1 → (False, mensagem de erro)."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("core.github_integration.subprocess.run", return_value=mock_result):
            client = GitHubClient()
            ok, msg = client.health_check()

        assert ok is False
        assert msg is not None
        assert len(msg) > 0

    def test_github_client_health_check_gh_not_found(self):
        """Mock FileNotFoundError → (False, mensagem de erro)."""
        with patch(
            "core.github_integration.subprocess.run",
            side_effect=FileNotFoundError("gh not installed"),
        ):
            client = GitHubClient()
            ok, msg = client.health_check()

        assert ok is False
        assert msg is not None
        assert len(msg) > 0


# ---------------------------------------------------------------------------
# Grupo 4 — _resolve_from_github e traceability
# ---------------------------------------------------------------------------


class TestResolveFromGitHub:
    def _make_github_issue(self, issue_number=152) -> GitHubIssue:
        return GitHubIssue(
            issue_number=issue_number,
            title="Add OAuth login",
            body="## Acceptance Criteria\n- user can log in with GitHub\n- token is stored securely",
            state="open",
            labels=["feature", "auth"],
            url=f"https://github.com/org/repo/issues/{issue_number}",
            milestone="v2.4",
        )

    def test_traceability_resolves_github_issue(self):
        """Mock GitHubClient.get_issue retornando GitHubIssue → TracedTo com source='github'."""
        github_cfg = {"repo": "org/repo", "source": "gh-cli"}
        issue = self._make_github_issue()

        with patch("core.github_integration.GitHubClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.get_issue.return_value = issue
            MockClient.return_value = mock_instance

            result = _resolve_from_github(152, github_cfg)

        assert result is not None
        assert isinstance(result, TracedTo)
        assert result.source == "github"

    def test_traceability_github_fallback_on_error(self):
        """Mock GitHubClient.get_issue retornando GitHubError → retorna None."""
        github_cfg = {"repo": "org/repo", "source": "gh-cli"}
        error = GitHubError(reason="not found", next_action="check issue number")

        with patch("core.github_integration.GitHubClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.get_issue.return_value = error
            MockClient.return_value = mock_instance

            result = _resolve_from_github(999, github_cfg)

        assert result is None

    def test_traceability_github_body_as_ac(self):
        """Verifica que body do Issue está em acceptance_criteria do TracedTo."""
        github_cfg = {"repo": "org/repo", "source": "gh-cli"}
        issue = self._make_github_issue()

        with patch("core.github_integration.GitHubClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.get_issue.return_value = issue
            MockClient.return_value = mock_instance

            result = _resolve_from_github(152, github_cfg)

        assert result is not None
        assert result.acceptance_criteria == issue.body
        assert "Acceptance Criteria" in result.acceptance_criteria

    def test_traceability_github_ticket_id_format(self):
        """ticket_id do TracedTo deve ser '#152' quando vem do GitHub."""
        github_cfg = {"repo": "org/repo", "source": "gh-cli"}
        issue = self._make_github_issue(issue_number=152)

        with patch("core.github_integration.GitHubClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.get_issue.return_value = issue
            MockClient.return_value = mock_instance

            result = _resolve_from_github(152, github_cfg)

        assert result is not None
        assert result.ticket_id == "#152"

    def test_traceability_github_labels_as_components(self):
        """labels do Issue são mapeados para components do TracedTo."""
        github_cfg = {"repo": "org/repo", "source": "gh-cli"}
        issue = self._make_github_issue()

        with patch("core.github_integration.GitHubClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.get_issue.return_value = issue
            MockClient.return_value = mock_instance

            result = _resolve_from_github(152, github_cfg)

        assert result is not None
        assert "feature" in result.components
        assert "auth" in result.components


# ---------------------------------------------------------------------------
# Grupo 5 — _post_github_pr_comment
# ---------------------------------------------------------------------------


class TestPostGitHubPrComment:
    def test_post_pr_comment_skipped_when_disabled(self, tmp_path):
        """comment_on_pr=False → subprocess NÃO é chamado."""
        from core.orchestrator import _post_github_pr_comment

        review_path = tmp_path / "REVIEW.md"
        review_path.write_text("# Review", encoding="utf-8")
        target_data = {"output": {"comment_on_pr": False}}

        with patch("core.orchestrator.subprocess.run") as mock_run:
            _post_github_pr_comment(review_path, "feat/152", target_data)

        mock_run.assert_not_called()

    def test_post_pr_comment_calls_gh_cli(self, tmp_path):
        """comment_on_pr=True + pr_platform='github' → subprocess chamado com gh pr comment."""
        from core.orchestrator import _post_github_pr_comment

        review_path = tmp_path / "REVIEW.md"
        review_path.write_text("# Review", encoding="utf-8")
        target_data = {
            "output": {
                "comment_on_pr": True,
                "pr_platform": "github",
            }
        }

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("core.orchestrator.subprocess.run", return_value=mock_result) as mock_run:
            _post_github_pr_comment(review_path, "feat/152", target_data)

        mock_run.assert_called_once()
        called_cmd = mock_run.call_args[0][0]
        assert "gh" in called_cmd
        assert "pr" in called_cmd
        assert "comment" in called_cmd
        assert "feat/152" in called_cmd
        assert "--body-file" in called_cmd

    def test_post_pr_comment_graceful_on_gh_error(self, tmp_path):
        """subprocess levanta CalledProcessError → sem raise (não propaga)."""
        import subprocess as _subprocess
        from core.orchestrator import _post_github_pr_comment

        review_path = tmp_path / "REVIEW.md"
        review_path.write_text("# Review", encoding="utf-8")
        target_data = {
            "output": {
                "comment_on_pr": True,
                "pr_platform": "github",
            }
        }

        with patch(
            "core.orchestrator.subprocess.run",
            side_effect=_subprocess.CalledProcessError(1, "gh", stderr="PR not found"),
        ):
            # Não deve lançar exceção
            _post_github_pr_comment(review_path, "feat/152", target_data)

    def test_post_pr_comment_graceful_on_file_not_found(self, tmp_path):
        """subprocess levanta FileNotFoundError → sem raise (não propaga)."""
        from core.orchestrator import _post_github_pr_comment

        review_path = tmp_path / "REVIEW.md"
        review_path.write_text("# Review", encoding="utf-8")
        target_data = {
            "output": {
                "comment_on_pr": True,
                "pr_platform": "github",
            }
        }

        with patch(
            "core.orchestrator.subprocess.run",
            side_effect=FileNotFoundError("gh not installed"),
        ):
            # Não deve lançar exceção
            _post_github_pr_comment(review_path, "feat/152", target_data)

    def test_post_pr_comment_skipped_when_platform_not_github(self, tmp_path):
        """pr_platform diferente de 'github' → subprocess NÃO é chamado."""
        from core.orchestrator import _post_github_pr_comment

        review_path = tmp_path / "REVIEW.md"
        review_path.write_text("# Review", encoding="utf-8")
        target_data = {
            "output": {
                "comment_on_pr": True,
                "pr_platform": "gitlab",
            }
        }

        with patch("core.orchestrator.subprocess.run") as mock_run:
            _post_github_pr_comment(review_path, "feat/152", target_data)

        mock_run.assert_not_called()
