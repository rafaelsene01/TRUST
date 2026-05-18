"""HTTP grounding adapter.

Reads grounding documents from authenticated HTTP/HTTPS endpoints —
Confluence, internal wikis, or any REST API that returns Markdown or HTML.

Authentication:
    Set the token in an env var and reference it in trust.config.yaml:

    ```yaml
    grounding:
      sources:
        - id: "confluence"
          adapter: "http"
          base_url: "https://wiki.company.com/api/v2"
          auth:
            type: "bearer"
            token_env: "CONFLUENCE_TOKEN"
          volatile: true
    ```

    Supported auth types:
    - ``bearer`` — Authorization: Bearer <token>
    - ``basic``  — Authorization: Basic base64(user:password)
    - ``header`` — custom header name + token env var

Cache:
    Responses are cached on disk (default TTL: 60 minutes).
    Configure with ``cache_ttl_minutes`` in the source config.
    Volatile sources still cache, but hash mismatches don't HALT.

Content negotiation:
    - If the response Content-Type is ``text/html``, basic HTML-to-text
      stripping is applied (no lxml dependency — stdlib only).
    - If it's ``application/json``, the response is JSON-serialised to
      a readable Markdown representation.
    - All other types are returned as-is (assumed to be Markdown or plain text).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class HttpDocContent:
    path: str
    url: str
    content: str
    sha256: str
    fetched_at: str
    content_type: str
    status_code: int


@dataclass
class HttpHealthStatus:
    ok: bool
    error: str | None = None
    next_action: str | None = None


# ---------------------------------------------------------------------------
# HTML stripping (stdlib only)
# ---------------------------------------------------------------------------


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\n{3,}")


def _html_to_text(html: str) -> str:
    text = html
    # Remove <head> block
    text = re.sub(r"<head[^>]*>.*?</head>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Convert block elements to newlines
    for tag in ("p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
        text = re.sub(rf"</?{tag}[^>]*>", "\n", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = _HTML_TAG_RE.sub("", text)
    # Decode common HTML entities
    for entity, char in (
        ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
        ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " "),
    ):
        text = text.replace(entity, char)
    text = _WHITESPACE_RE.sub("\n\n", text)
    return text.strip()


def _json_to_markdown(data: object, source_url: str) -> str:
    """Convert a JSON response to a readable Markdown representation."""
    try:
        body = json.dumps(data, indent=2, ensure_ascii=False)
    except TypeError:
        body = str(data)
    return f"# JSON response from `{source_url}`\n\n```json\n{body}\n```"


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _build_auth_header(auth_config: dict) -> tuple[str, str] | None:
    """Build (header_name, header_value) from auth config. Returns None if no auth."""
    auth_type = auth_config.get("type", "").lower()

    if auth_type == "bearer":
        token_env = auth_config.get("token_env", "")
        token = os.environ.get(token_env, "").strip()
        if not token:
            raise ValueError(
                f"Bearer token env var '{token_env}' is not set or empty.\n"
                f"  Next action: export {token_env}=<your-token> in your shell, "
                f"or add it to .env.local"
            )
        return "Authorization", f"Bearer {token}"

    if auth_type == "basic":
        user_env = auth_config.get("user_env", "")
        pass_env = auth_config.get("password_env", "")
        user = os.environ.get(user_env, "").strip()
        pwd = os.environ.get(pass_env, "").strip()
        if not user or not pwd:
            missing = [v for v, val in ((user_env, user), (pass_env, pwd)) if not val]
            raise ValueError(
                f"Basic auth env vars not set: {missing}.\n"
                f"  Next action: set both {user_env} and {pass_env} in your environment."
            )
        encoded = base64.b64encode(f"{user}:{pwd}".encode()).decode()
        return "Authorization", f"Basic {encoded}"

    if auth_type == "header":
        header_name = auth_config.get("header_name", "X-Auth-Token")
        token_env = auth_config.get("token_env", "")
        token = os.environ.get(token_env, "").strip()
        if not token:
            raise ValueError(
                f"Custom header token env var '{token_env}' is not set.\n"
                f"  Next action: export {token_env}=<your-token>"
            )
        return header_name, token

    return None


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class HttpAdapter:
    """Reads grounding docs from authenticated HTTP/HTTPS endpoints.

    Args:
        base_url:    Base URL (e.g. ``https://wiki.company.com/api/v2``).
        auth_config: Dict with keys: ``type``, ``token_env`` (or equivalents).
        cache:       Optional SourceCache. If None, caching is disabled.
        timeout_s:   HTTP request timeout in seconds (default: 15).
        volatile:    If True, hash mismatches don't trigger HALT (see above).
    """

    def __init__(
        self,
        base_url: str,
        auth_config: dict | None = None,
        cache=None,
        timeout_s: int = 15,
        volatile: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.auth_config = auth_config or {}
        self.cache = cache
        self.timeout_s = timeout_s
        self.volatile = volatile

    def _full_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    def _fetch(self, url: str) -> tuple[str, str, int]:
        """Fetch URL, return (content_text, content_type, status_code).

        Raises:
            ValueError: On auth config errors (actionable message).
            ConnectionError: On network/HTTP errors (actionable message).
        """
        req = urllib.request.Request(url)
        req.add_header("Accept", "text/markdown, text/plain, text/html, application/json")
        req.add_header("User-Agent", "TRUST-Framework/1.1")

        if self.auth_config:
            auth_header = _build_auth_header(self.auth_config)
            if auth_header:
                req.add_header(*auth_header)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                status = resp.status
                ct = resp.headers.get("Content-Type", "text/plain")
                raw_bytes = resp.read()
                encoding = "utf-8"
                charset_match = re.search(r"charset=([\w-]+)", ct)
                if charset_match:
                    encoding = charset_match.group(1)
                raw_text = raw_bytes.decode(encoding, errors="replace")
                return raw_text, ct.split(";")[0].strip(), status

        except urllib.error.HTTPError as exc:
            hint = {
                401: f"Run: export {self.auth_config.get('token_env', 'TOKEN')}=<valid-token>",
                403: "Token may lack permission to this resource. Check your wiki/Confluence ACL.",
                404: f"Resource not found at {url}. Check the path in trust.config.yaml.",
                429: "Rate limited. Increase cache TTL or wait and retry.",
                500: "Server error. Check the server logs or contact the wiki admin.",
            }.get(exc.code, f"HTTP {exc.code}: check the URL and credentials.")
            raise ConnectionError(
                f"HTTP {exc.code} fetching {url}\n  Next action: {hint}"
            ) from exc

        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"Cannot reach {url}: {exc.reason}\n"
                f"  Next action: check network connectivity and that the URL is correct."
            ) from exc

        except TimeoutError:
            raise ConnectionError(
                f"Request to {url} timed out after {self.timeout_s}s.\n"
                f"  Next action: increase timeout_s in config, or check network latency."
            ) from None

    def _normalise_content(self, raw: str, content_type: str, url: str) -> str:
        if "text/html" in content_type:
            return _html_to_text(raw)
        if "application/json" in content_type:
            try:
                data = json.loads(raw)
                return _json_to_markdown(data, url)
            except json.JSONDecodeError:
                return raw
        return raw

    def health_check(self) -> HttpHealthStatus:
        """Verify that base_url is reachable and auth is configured."""
        try:
            _build_auth_header(self.auth_config)
        except ValueError as exc:
            return HttpHealthStatus(
                ok=False,
                error=str(exc),
                next_action="Set the missing environment variables listed above.",
            )

        try:
            self._fetch(self.base_url)
            return HttpHealthStatus(ok=True)
        except ConnectionError as exc:
            return HttpHealthStatus(
                ok=False,
                error=str(exc),
                next_action="Check network connectivity and credentials.",
            )
        except Exception as exc:
            return HttpHealthStatus(
                ok=False,
                error=f"Unexpected error: {exc}",
                next_action="Run /trust doctor for a full diagnostic.",
            )

    def read(self, path: str, source_id: str = "http") -> HttpDocContent:
        """Fetch a document from the HTTP source.

        Checks the cache first. On cache miss, fetches from the network
        and stores in cache.

        Args:
            path:      Relative path or full URL.
            source_id: Source ID used for cache keying.

        Returns:
            HttpDocContent with the document text and metadata.

        Raises:
            ValueError:      Auth config errors.
            ConnectionError: Network/HTTP errors.
        """
        url = self._full_url(path)

        # Cache lookup
        if self.cache is not None:
            cached = self.cache.get(source_id, path)
            if cached is not None:
                return HttpDocContent(
                    path=path,
                    url=url,
                    content=cached.content,
                    sha256=cached.sha256,
                    fetched_at=cached.fetched_at,
                    content_type="text/cached",
                    status_code=200,
                )

        raw, content_type, status = self._fetch(url)
        content = self._normalise_content(raw, content_type, url)
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        fetched_at = datetime.now(tz=timezone.utc).isoformat()

        if self.cache is not None:
            self.cache.put(source_id, path, content, sha256)

        return HttpDocContent(
            path=path,
            url=url,
            content=content,
            sha256=sha256,
            fetched_at=fetched_at,
            content_type=content_type,
            status_code=status,
        )
