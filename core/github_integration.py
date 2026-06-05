"""GitHub integration for TRUST Phase 6 — Rastreabilidade.

Resolves a branch name to a GitHub Issue number and fetches Issue metadata
via the `gh` CLI so findings can be linked to the requirement that originated
the change.

Configuration in trust.config.yaml:

    ```yaml
    integrations:
      github:
        source: gh-cli         # auto | mcp | gh-cli | disabled
        repo: ""               # owner/repo — leave empty to auto-detect from cwd
        branch_pattern: "(?:feat|fix|chore|refactor|docs|test)/(?P<issue>\\d+)"
    ```

Usage:
    from core.github_integration import GitHubClient, extract_issue_number
    number = extract_issue_number("feat/152")  # -> 152
    client = GitHubClient()
    issue = client.get_issue(152)
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class GitHubIssue:
    """Resolved GitHub Issue metadata."""

    issue_number: int
    title: str
    body: str               # corpo completo do Issue = contexto/AC do card
    state: str              # "open" | "closed"
    labels: list[str]
    url: str
    milestone: str          # milestone name ou ""


@dataclass
class GitHubError:
    """Describes a failed GitHub Issue resolution."""

    reason: str
    next_action: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_DEFAULT_GH_BRANCH_PATTERN = r"(?:feat|fix|chore|refactor|docs|test)/(?P<issue>\d+)"


def extract_issue_number(branch: str, pattern: str | None = None) -> int | None:
    """Extrai número do Issue do nome do branch.

    Suporta: feat/152, feat/256-descricao, fix/#123
    Fallback: primeiro número encontrado no branch após '/'

    Args:
        branch:  Branch name, e.g. ``feat/152`` or ``fix/#123-fix-login``.
        pattern: Optional regex pattern with a named group ``(?P<issue>...)``.

    Returns:
        Issue number as int, or ``None`` if no match.
    """
    compiled = re.compile(pattern or _DEFAULT_GH_BRANCH_PATTERN)
    m = compiled.search(branch)
    if m:
        try:
            return int(m.group("issue"))
        except (IndexError, ValueError):
            pass

    # Fallback: procurar #?\d+ após uma '/' no branch
    fallback = re.search(r"/#?(\d+)", branch)
    if fallback:
        return int(fallback.group(1))

    return None


# ---------------------------------------------------------------------------
# GitHub client
# ---------------------------------------------------------------------------


class GitHubClient:
    """Wrapper para `gh issue view` via subprocess."""

    def __init__(self, repo: str | None = None, timeout_s: int = 10):
        """Initialise the GitHub client.

        Args:
            repo:      ``"owner/repo"`` or ``None`` to auto-detect from cwd.
            timeout_s: subprocess timeout in seconds.
        """
        self.repo = repo
        self.timeout_s = timeout_s

    def health_check(self) -> tuple[bool, str | None]:
        """Roda `gh auth status`; retorna (ok, error_msg)."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                timeout=self.timeout_s,
            )
            if result.returncode == 0:
                return (True, None)
            return (
                False,
                "gh não autenticado.\n   Next action: rode `gh auth login`",
            )
        except FileNotFoundError:
            return (
                False,
                "gh CLI não encontrado.\n   Next action: instale em https://cli.github.com e rode `gh auth login`",
            )

    def get_issue(self, number: int) -> GitHubIssue | GitHubError:
        """Roda `gh issue view <N> --json ...` e retorna GitHubIssue ou GitHubError.

        Args:
            number: GitHub Issue number.

        Returns:
            :class:`GitHubIssue` on success, :class:`GitHubError` on failure.
        """
        cmd = [
            "gh",
            "issue",
            "view",
            str(number),
            "--json",
            "number,title,body,labels,state,url,milestone",
        ]
        if self.repo:
            cmd += ["--repo", self.repo]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
            )
        except FileNotFoundError:
            return GitHubError(
                reason="gh CLI não encontrado",
                next_action="instale em https://cli.github.com",
            )
        except subprocess.TimeoutExpired:
            return GitHubError(
                reason="timeout",
                next_action="verifique sua conexão",
            )

        if result.returncode != 0:
            return GitHubError(
                reason=result.stderr,
                next_action=f"verifique se o Issue #{number} existe",
            )

        data = json.loads(result.stdout)

        labels: list[str] = [lbl["name"] for lbl in data.get("labels", [])]

        milestone_raw = data.get("milestone", {}) or {}
        milestone: str = milestone_raw.get("title", "") if isinstance(milestone_raw, dict) else ""

        return GitHubIssue(
            issue_number=data["number"],
            title=data.get("title", ""),
            body=data.get("body", ""),
            state=data.get("state", ""),
            labels=labels,
            url=data.get("url", ""),
            milestone=milestone,
        )
