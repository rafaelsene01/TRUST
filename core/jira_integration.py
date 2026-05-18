"""Jira integration for TRUST Phase 6 — Rastreabilidade.

Resolves a branch name to a Jira ticket ID and fetches ticket metadata
so findings can be linked to the requirement that originated the change.

Configuration in trust.config.yaml:

    ```yaml
    traceability:
      enabled: true
      jira:
        base_url: "https://empresa.atlassian.net"
        project_keys: ["PAY", "AUTH", "PLAT"]
        auth:
          user_env: "JIRA_USER"
          token_env: "JIRA_TOKEN"
      branch_pattern: "(?:feat|fix|chore)/({ticket})"
    ```

Auth:
    Jira Cloud uses Basic auth: base64(user:api_token).
    Set JIRA_USER (your email) and JIRA_TOKEN (API token from
    https://id.atlassian.com/manage-profile/security/api-tokens).

Branch pattern:
    A regex with a named group ``{ticket}`` (replaced internally to
    ``(?P<ticket>...)``) that captures the ticket ID from the branch name.

    Default: matches branches like feat/PAY-123, fix/AUTH-88-some-desc
    ``(?:feat|fix|chore|refactor|test)/({ticket}[A-Z]+-\\d+)``
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class JiraTicket:
    """Resolved Jira ticket metadata."""

    ticket_id: str              # e.g. "PAY-123"
    summary: str
    description: str            # plain text, stripped of Atlassian Document Format
    status: str                 # e.g. "In Progress"
    issue_type: str             # e.g. "Story", "Bug", "Task"
    url: str                    # browser URL to the ticket
    acceptance_criteria: str    # extracted from description if present
    labels: list[str] = field(default_factory=list)
    components: list[str] = field(default_factory=list)


@dataclass
class JiraError:
    """Describes a failed Jira resolution."""

    reason: str
    next_action: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_DEFAULT_BRANCH_PATTERN = r"(?:feat|fix|chore|refactor|test)/(?P<ticket>[A-Z]+-\d+)"


def _compile_pattern(raw: str) -> re.Pattern:
    """Compile branch_pattern, replacing ``{ticket}`` with a named group."""
    # Allow both {ticket} shorthand and explicit (?P<ticket>...)
    if "{ticket}" in raw:
        raw = raw.replace("{ticket}", "(?P<ticket>[A-Z]+-\\d+)")
    elif "(?P<ticket>" not in raw:
        # Wrap entire pattern as the ticket group if no group named
        raw = f"(?P<ticket>{raw})"
    return re.compile(raw, re.IGNORECASE)


def extract_ticket_id(branch: str, pattern: str | None = None) -> str | None:
    """Extract a Jira ticket ID from a branch name.

    Args:
        branch:  Branch name, e.g. ``feat/PAY-123`` or ``PAY-123-fix-login``.
        pattern: Optional regex pattern (see module docstring).

    Returns:
        Ticket ID like ``"PAY-123"``, or ``None`` if no match.
    """
    compiled = _compile_pattern(pattern or _DEFAULT_BRANCH_PATTERN)
    m = compiled.search(branch)
    if m:
        ticket = m.group("ticket").upper()
        return ticket

    # Fallback: look for bare PROJECT-NNN anywhere in the branch name
    fallback = re.search(r"[A-Z]+-\d+", branch.upper())
    return fallback.group(0) if fallback else None


def _build_auth_header(user_env: str, token_env: str) -> str:
    """Build Basic auth header value for Jira Cloud."""
    user = os.environ.get(user_env, "").strip()
    token = os.environ.get(token_env, "").strip()
    if not user or not token:
        missing = [v for v, val in ((user_env, user), (token_env, token)) if not val]
        raise ValueError(
            f"Jira auth env vars not set: {missing}.\n"
            f"  Next action: export {user_env}=your@email.com "
            f"and {token_env}=<api-token>\n"
            f"  Get API token: https://id.atlassian.com/manage-profile/security/api-tokens"
        )
    encoded = base64.b64encode(f"{user}:{token}".encode()).decode()
    return f"Basic {encoded}"


def _adf_to_text(node: object, depth: int = 0) -> str:
    """Convert Atlassian Document Format (ADF) node to plain text."""
    if not isinstance(node, dict):
        return ""

    node_type = node.get("type", "")
    content = node.get("content", [])
    text = node.get("text", "")

    if node_type == "text":
        return text

    if node_type in ("paragraph", "blockquote"):
        inner = "".join(_adf_to_text(c) for c in content)
        return inner + "\n"

    if node_type in ("heading",):
        level = node.get("attrs", {}).get("level", 1)
        inner = "".join(_adf_to_text(c) for c in content)
        return "#" * level + " " + inner + "\n"

    if node_type in ("bulletList", "orderedList"):
        return "".join(_adf_to_text(c, depth + 1) for c in content)

    if node_type == "listItem":
        prefix = "  " * depth + "- "
        inner = "".join(_adf_to_text(c, depth) for c in content).strip()
        return prefix + inner + "\n"

    if node_type == "codeBlock":
        lang = node.get("attrs", {}).get("language", "")
        inner = "".join(_adf_to_text(c) for c in content)
        return f"```{lang}\n{inner}\n```\n"

    if node_type == "inlineCard":
        url = node.get("attrs", {}).get("url", "")
        return f"[{url}]({url})"

    if node_type == "hardBreak":
        return "\n"

    if node_type == "rule":
        return "---\n"

    # For any container node, recurse into content
    return "".join(_adf_to_text(c, depth) for c in content)


def _extract_acceptance_criteria(description_text: str) -> str:
    """Extract acceptance criteria section from plain text description."""
    patterns = [
        r"(?:acceptance criteria|critérios de aceite|ac)[:\s]*\n(.*?)(?=\n#|\Z)",
        r"(?:given|dado)[^\n]*\n(.*?)(?=\n#|\Z)",
    ]
    for pat in patterns:
        m = re.search(pat, description_text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return ""


# ---------------------------------------------------------------------------
# Jira client
# ---------------------------------------------------------------------------


class JiraClient:
    """Lightweight Jira REST API v3 client.

    Args:
        base_url:  Jira Cloud base URL, e.g. ``https://empresa.atlassian.net``.
        user_env:  Env var name for the Jira user (email).
        token_env: Env var name for the Jira API token.
        timeout_s: HTTP timeout in seconds.
    """

    def __init__(
        self,
        base_url: str,
        user_env: str = "JIRA_USER",
        token_env: str = "JIRA_TOKEN",
        timeout_s: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.user_env = user_env
        self.token_env = token_env
        self.timeout_s = timeout_s

    def _request(self, path: str) -> dict:
        url = f"{self.base_url}/rest/api/3/{path.lstrip('/')}"
        auth = _build_auth_header(self.user_env, self.token_env)
        req = urllib.request.Request(url)
        req.add_header("Authorization", auth)
        req.add_header("Accept", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            hints = {
                401: (
                    f"Invalid credentials. Check {self.user_env} and {self.token_env}.\n"
                    f"  Next action: generate a fresh API token at "
                    f"https://id.atlassian.com/manage-profile/security/api-tokens"
                ),
                403: (
                    "Permission denied. Your Jira user may not have access to this project.\n"
                    "  Next action: ask your Jira admin to grant Browse permission."
                ),
                404: (
                    f"Ticket not found. Check the project key and ticket number.\n"
                    f"  URL tried: {url}"
                ),
                429: (
                    "Jira rate limit hit.\n"
                    "  Next action: wait a moment and retry, or increase cache TTL."
                ),
            }
            raise ConnectionError(hints.get(exc.code, f"HTTP {exc.code} from Jira: {url}")) from exc

        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"Cannot reach Jira at {self.base_url}: {exc.reason}\n"
                f"  Next action: check network connectivity and that JIRA base_url is correct."
            ) from exc

    def health_check(self) -> tuple[bool, str | None]:
        """Return (ok, error_msg). error_msg includes next_action if not ok."""
        try:
            _build_auth_header(self.user_env, self.token_env)
            self._request("myself")
            return True, None
        except (ValueError, ConnectionError) as exc:
            return False, str(exc)

    def get_ticket(self, ticket_id: str) -> JiraTicket | JiraError:
        """Fetch a Jira ticket and return its metadata.

        Returns JiraTicket on success, JiraError on failure.
        """
        try:
            data = self._request(
                f"issue/{ticket_id}?fields=summary,description,status,issuetype,labels,components"
            )
        except ValueError as exc:
            return JiraError(reason=str(exc), next_action="Set the missing env vars.")
        except ConnectionError as exc:
            return JiraError(reason=str(exc), next_action="Check the error message above.")

        fields = data.get("fields", {})

        # Description may be ADF (dict) or plain text (str) or None
        raw_desc = fields.get("description")
        if isinstance(raw_desc, dict):
            description = _adf_to_text(raw_desc).strip()
        elif isinstance(raw_desc, str):
            description = raw_desc.strip()
        else:
            description = ""

        ac = _extract_acceptance_criteria(description)

        return JiraTicket(
            ticket_id=ticket_id,
            summary=fields.get("summary", ""),
            description=description,
            status=fields.get("status", {}).get("name", "Unknown"),
            issue_type=fields.get("issuetype", {}).get("name", ""),
            url=f"{self.base_url}/browse/{ticket_id}",
            acceptance_criteria=ac,
            labels=[lbl for lbl in fields.get("labels", [])],
            components=[c.get("name", "") for c in fields.get("components", [])],
        )
