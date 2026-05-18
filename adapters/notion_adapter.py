"""Notion grounding adapter.

Reads grounding documents from Notion pages and databases via the
Notion REST API v1 (api.notion.com).

Configuration in trust.config.yaml:

    ```yaml
    grounding:
      sources:
        - id: "notion-docs"
          adapter: "notion"
          auth:
            token_env: "NOTION_TOKEN"       # required: Integration token
          volatile: true                    # Notion content changes → don't HALT on hash change
          cache_ttl_minutes: 60
    ```

    Per-document path format:
    - Page by ID:       ``page:<page-id>``
    - Database query:   ``db:<database-id>``
    - Page by URL:      ``https://www.notion.so/...`` (ID extracted automatically)

Getting a Notion Integration token:
    1. Go to https://www.notion.so/my-integrations
    2. Create a new internal integration
    3. Copy the "Internal Integration Secret"
    4. Add the integration to each page/database you want TRUST to read

The adapter converts Notion blocks to Markdown. Not all block types are
supported — unsupported blocks emit a ``<!-- unsupported: <type> -->`` comment
so the grounding doc is still usable.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone


NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"
_PAGE_ID_RE = re.compile(r"[a-f0-9]{32}|[a-f0-9-]{36}", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class NotionDocContent:
    path: str
    page_id: str
    title: str
    content: str
    sha256: str
    fetched_at: str
    last_edited_time: str | None = None


@dataclass
class NotionHealthStatus:
    ok: bool
    error: str | None = None
    next_action: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_page_id(path: str) -> str:
    """Extract a Notion page/database ID from a path or URL."""
    # Already a bare ID (32 hex chars or UUID format)
    if _PAGE_ID_RE.fullmatch(path.replace("-", "")):
        return path.replace("-", "")

    # page:<id> or db:<id>
    if ":" in path and not path.startswith("http"):
        _, raw_id = path.split(":", 1)
        cleaned = raw_id.strip().replace("-", "")
        if _PAGE_ID_RE.fullmatch(cleaned):
            return cleaned

    # Notion URL: the page ID is the last hyphen-separated segment of the path
    # e.g. https://www.notion.so/My-Page-Title-a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
    if "notion.so" in path or path.startswith("http"):
        # Split path component and take last segment
        path_part = path.split("?")[0].rstrip("/")
        last_segment = path_part.split("/")[-1]
        # The ID is the last 32-char hex run in the segment (after slug words)
        cleaned = last_segment.replace("-", "")
        # Find the rightmost 32-char hex sequence
        for i in range(len(cleaned) - 31, -1, -1):
            candidate = cleaned[i:i + 32]
            if _PAGE_ID_RE.fullmatch(candidate):
                return candidate

    raise ValueError(
        f"Cannot extract Notion page ID from: {path!r}\n"
        f"  Expected formats: 'page:<id>', 'db:<id>', "
        f"'https://notion.so/...', or a bare 32-char hex ID."
    )


def _plain_text(rich_text: list[dict]) -> str:
    return "".join(seg.get("plain_text", "") for seg in rich_text)


def _block_to_markdown(block: dict) -> str:
    """Convert a single Notion block to Markdown text."""
    btype = block.get("type", "")
    data = block.get(btype, {})

    if btype in ("paragraph",):
        text = _plain_text(data.get("rich_text", []))
        return text + "\n"

    if btype in ("heading_1",):
        return "# " + _plain_text(data.get("rich_text", [])) + "\n"

    if btype in ("heading_2",):
        return "## " + _plain_text(data.get("rich_text", [])) + "\n"

    if btype in ("heading_3",):
        return "### " + _plain_text(data.get("rich_text", [])) + "\n"

    if btype in ("bulleted_list_item",):
        return "- " + _plain_text(data.get("rich_text", [])) + "\n"

    if btype in ("numbered_list_item",):
        return "1. " + _plain_text(data.get("rich_text", [])) + "\n"

    if btype in ("to_do",):
        checked = "x" if data.get("checked") else " "
        return f"- [{checked}] " + _plain_text(data.get("rich_text", [])) + "\n"

    if btype in ("toggle",):
        return "> " + _plain_text(data.get("rich_text", [])) + "\n"

    if btype in ("quote",):
        text = _plain_text(data.get("rich_text", []))
        return "> " + text + "\n"

    if btype in ("callout",):
        icon = data.get("icon", {}).get("emoji", "💡")
        text = _plain_text(data.get("rich_text", []))
        return f"> {icon} {text}\n"

    if btype in ("code",):
        lang = data.get("language", "")
        text = _plain_text(data.get("rich_text", []))
        return f"```{lang}\n{text}\n```\n"

    if btype in ("divider",):
        return "---\n"

    if btype in ("table_of_contents", "breadcrumb", "unsupported"):
        return ""

    if btype in ("image",):
        img_data = data.get("external", {}) or data.get("file", {})
        url = img_data.get("url", "")
        caption = _plain_text(data.get("caption", []))
        return f"![{caption}]({url})\n"

    if btype in ("bookmark", "link_preview"):
        url = data.get("url", "")
        return f"[{url}]({url})\n"

    if btype in ("child_page",):
        title = data.get("title", "")
        return f"**→ Child page:** {title}\n"

    if btype in ("table",):
        # Tables need child blocks — we just emit a placeholder
        return "<!-- table: expand via child blocks -->\n"

    # Unknown block type — emit a comment so grounding doc is still parsable
    return f"<!-- unsupported block type: {btype} -->\n"


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class NotionAdapter:
    """Reads grounding docs from Notion pages and databases.

    Args:
        token_env:         Name of the env var holding the Notion token.
        cache:             Optional SourceCache.
        max_blocks:        Max blocks to fetch per page (default: 500).
        volatile:          If True, hash mismatches don't trigger HALT.
    """

    def __init__(
        self,
        token_env: str = "NOTION_TOKEN",
        cache=None,
        max_blocks: int = 500,
        volatile: bool = True,
    ):
        self.token_env = token_env
        self.cache = cache
        self.max_blocks = max_blocks
        self.volatile = volatile

    def _token(self) -> str:
        token = os.environ.get(self.token_env, "").strip()
        if not token:
            raise ValueError(
                f"Notion token env var '{self.token_env}' is not set.\n"
                f"  Next action: export {self.token_env}=secret_... "
                f"(get it from https://www.notion.so/my-integrations)"
            )
        return token

    def _request(self, endpoint: str, method: str = "GET", body: dict | None = None) -> dict:
        """Make an authenticated Notion API request."""
        url = f"{NOTION_BASE_URL}/{endpoint.lstrip('/')}"
        data = json.dumps(body).encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._token()}")
        req.add_header("Notion-Version", NOTION_API_VERSION)
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            error_msg = ""
            try:
                error_msg = json.loads(body_text).get("message", "")
            except Exception:
                error_msg = body_text[:200]

            hints = {
                401: (
                    f"Invalid Notion token. Check {self.token_env} is set correctly.\n"
                    f"  Next action: verify the token at https://www.notion.so/my-integrations"
                ),
                403: (
                    "The integration doesn't have access to this page/database.\n"
                    "  Next action: open the page in Notion → Share → Invite your integration."
                ),
                404: (
                    f"Page/database not found. Check the ID is correct and the integration is invited.\n"
                    f"  Error: {error_msg}"
                ),
                429: (
                    "Notion API rate limit hit. Increase cache TTL to reduce API calls.\n"
                    "  Next action: set cache_ttl_minutes: 120 in trust.config.yaml"
                ),
            }
            hint = hints.get(exc.code, f"HTTP {exc.code}: {error_msg}")
            raise ConnectionError(f"Notion API error: {hint}") from exc

        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"Cannot reach Notion API: {exc.reason}\n"
                f"  Next action: check network connectivity."
            ) from exc

    def _fetch_page_title(self, page_id: str) -> tuple[str, str | None]:
        """Return (title, last_edited_time) for a page."""
        page = self._request(f"pages/{page_id}")
        last_edited = page.get("last_edited_time")

        props = page.get("properties", {})
        # Try common title property names
        for key in ("Name", "Title", "title", "name"):
            prop = props.get(key, {})
            title_arr = prop.get("title", []) or prop.get("rich_text", [])
            if title_arr:
                return _plain_text(title_arr), last_edited

        return "Untitled", last_edited

    def _fetch_blocks(self, block_id: str) -> list[dict]:
        """Fetch all blocks for a page (handles pagination)."""
        blocks: list[dict] = []
        cursor: str | None = None
        fetched = 0

        while fetched < self.max_blocks:
            params = f"?page_size=100"
            if cursor:
                params += f"&start_cursor={cursor}"
            resp = self._request(f"blocks/{block_id}/children{params}")

            for block in resp.get("results", []):
                blocks.append(block)
                fetched += 1

            if not resp.get("has_more") or fetched >= self.max_blocks:
                break
            cursor = resp.get("next_cursor")

        return blocks

    def _fetch_database_items(self, database_id: str) -> str:
        """Fetch a database and return its contents as a Markdown table."""
        db = self._request(f"databases/{database_id}")
        title = _plain_text(db.get("title", []))

        # Query all pages in the database
        resp = self._request(
            f"databases/{database_id}/query",
            method="POST",
            body={"page_size": 100},
        )

        rows: list[dict[str, str]] = []
        columns: list[str] = []

        # Determine columns from first result
        results = resp.get("results", [])
        if results:
            columns = list(results[0].get("properties", {}).keys())

        for page in results:
            row: dict[str, str] = {}
            props = page.get("properties", {})
            for col in columns:
                prop = props.get(col, {})
                prop_type = prop.get("type", "")
                if prop_type == "title":
                    row[col] = _plain_text(prop.get("title", []))
                elif prop_type == "rich_text":
                    row[col] = _plain_text(prop.get("rich_text", []))
                elif prop_type == "select":
                    sel = prop.get("select")
                    row[col] = sel.get("name", "") if sel else ""
                elif prop_type == "multi_select":
                    row[col] = ", ".join(s.get("name", "") for s in prop.get("multi_select", []))
                elif prop_type == "checkbox":
                    row[col] = "✓" if prop.get("checkbox") else "✗"
                elif prop_type == "date":
                    date_obj = prop.get("date")
                    row[col] = date_obj.get("start", "") if date_obj else ""
                elif prop_type == "url":
                    row[col] = prop.get("url", "") or ""
                elif prop_type == "number":
                    num = prop.get("number")
                    row[col] = str(num) if num is not None else ""
                else:
                    row[col] = ""
            rows.append(row)

        # Build Markdown table
        lines = [f"# {title} (Notion Database)\n"]
        if columns:
            lines.append("| " + " | ".join(columns) + " |")
            lines.append("| " + " | ".join("---" for _ in columns) + " |")
            for row in rows:
                lines.append("| " + " | ".join(row.get(c, "") for c in columns) + " |")

        return "\n".join(lines)

    def _page_to_markdown(self, page_id: str) -> tuple[str, str, str | None]:
        """Convert a Notion page to Markdown. Returns (title, content, last_edited)."""
        title, last_edited = self._fetch_page_title(page_id)
        blocks = self._fetch_blocks(page_id)

        lines = [f"# {title}\n"]
        for block in blocks:
            lines.append(_block_to_markdown(block))

        content = "\n".join(lines)
        return title, content, last_edited

    def health_check(self) -> NotionHealthStatus:
        """Verify the Notion token is valid."""
        try:
            self._token()
            # Try a lightweight call to verify the token
            self._request("users/me")
            return NotionHealthStatus(ok=True)
        except ValueError as exc:
            return NotionHealthStatus(
                ok=False,
                error=str(exc),
                next_action=f"Set {self.token_env} in your environment.",
            )
        except ConnectionError as exc:
            return NotionHealthStatus(
                ok=False,
                error=str(exc),
                next_action="Check the error message above and follow the suggested action.",
            )
        except Exception as exc:
            return NotionHealthStatus(
                ok=False,
                error=f"Unexpected: {exc}",
                next_action="Run /trust doctor for a full diagnostic.",
            )

    def read(self, path: str, source_id: str = "notion") -> NotionDocContent:
        """Fetch a Notion page or database and return it as Markdown.

        Args:
            path:      Page ID, 'page:<id>', 'db:<id>', or full Notion URL.
            source_id: Source ID used for cache keying.

        Returns:
            NotionDocContent with the Markdown text and metadata.

        Raises:
            ValueError:      Token not set or invalid path format.
            ConnectionError: API / network errors (always includes next action).
        """
        # Cache lookup
        if self.cache is not None:
            cached = self.cache.get(source_id, path)
            if cached is not None:
                return NotionDocContent(
                    path=path,
                    page_id="cached",
                    title="cached",
                    content=cached.content,
                    sha256=cached.sha256,
                    fetched_at=cached.fetched_at,
                )

        page_id = _extract_page_id(path)
        is_database = path.startswith("db:")

        if is_database:
            content = self._fetch_database_items(page_id)
            title = "Database"
            last_edited = None
        else:
            title, content, last_edited = self._page_to_markdown(page_id)

        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        fetched_at = datetime.now(tz=timezone.utc).isoformat()

        if self.cache is not None:
            self.cache.put(source_id, path, content, sha256)

        return NotionDocContent(
            path=path,
            page_id=page_id,
            title=title,
            content=content,
            sha256=sha256,
            fetched_at=fetched_at,
            last_edited_time=last_edited,
        )
