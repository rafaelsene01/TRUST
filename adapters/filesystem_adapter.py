"""Filesystem grounding adapter.

Reads grounding documents from local disk — either in-repo,
from a developer's second brain, or from a shared synced folder.

This is the only adapter available in the MVP.
Notion and HTTP adapters land in v1.1.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocMetadata:
    path: str
    size_bytes: int
    last_modified: float


@dataclass
class DocContent:
    path: str
    content: str
    sha256: str
    fetched_at: str


@dataclass
class HealthStatus:
    ok: bool
    error: str | None = None


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resolve_base(base_path: str, setup_path: Path | None = None) -> Path:
    """Resolve base_path, substituting env vars and expanding ~."""
    # Substitute ${VAR:-default} and ${VAR}
    def replacer(match: re.Match) -> str:
        expr = match.group(1)
        if ":-" in expr:
            var, default = expr.split(":-", 1)
            return os.environ.get(var.strip(), default)
        return os.environ.get(expr.strip(), "")

    resolved = re.sub(r"\$\{([^}]+)\}", replacer, base_path)
    expanded = Path(resolved).expanduser()

    # Relative paths resolve against the setup repo root
    if not expanded.is_absolute() and setup_path:
        return (setup_path / expanded).resolve()

    return expanded.resolve()


class FilesystemAdapter:
    """Reads grounding docs from the local filesystem.

    Supports:
    - Single files: ``path = "06-security-policy.md"``
    - Directories: ``path = "07-adrs/"``  (loads all .md files recursively)
    - Glob patterns: ``path = "adrs/*.md"``
    """

    def __init__(self, base_path: str, setup_path: Path | None = None):
        self.base_path = base_path
        self.setup_path = setup_path
        self._resolved_base: Path | None = None

    def _base(self) -> Path:
        if self._resolved_base is None:
            self._resolved_base = _resolve_base(self.base_path, self.setup_path)
        return self._resolved_base

    def health_check(self) -> HealthStatus:
        """Verify the base path is accessible."""
        try:
            base = self._base()
            if not base.exists():
                return HealthStatus(
                    ok=False,
                    error=f"Base path does not exist: {base}",
                )
            if not os.access(base, os.R_OK):
                return HealthStatus(
                    ok=False,
                    error=f"Base path is not readable: {base}",
                )
            return HealthStatus(ok=True)
        except Exception as e:
            return HealthStatus(ok=False, error=str(e))

    def exists(self, path: str) -> bool:
        """Return True if the given path exists under the base."""
        full = self._base() / path
        # Also consider it exists if it's a directory
        return full.exists()

    def list(self, prefix: str = "") -> list[DocMetadata]:
        """List all documents under the base (optionally filtered by prefix)."""
        base = self._base()
        results = []

        search_path = base / prefix if prefix else base

        if search_path.is_file():
            stat = search_path.stat()
            results.append(
                DocMetadata(
                    path=str(search_path.relative_to(base)),
                    size_bytes=stat.st_size,
                    last_modified=stat.st_mtime,
                )
            )
        elif search_path.is_dir():
            for f in sorted(search_path.rglob("*.md")):
                stat = f.stat()
                results.append(
                    DocMetadata(
                        path=str(f.relative_to(base)),
                        size_bytes=stat.st_size,
                        last_modified=stat.st_mtime,
                    )
                )

        return results

    def read(self, path: str) -> DocContent:
        """Read a document (or all docs in a directory) and return content.

        If ``path`` points to a directory, all .md files inside are read
        and concatenated with a separator.

        Args:
            path: Relative path within the base directory.

        Returns:
            DocContent with full text, sha256, and timestamp.

        Raises:
            FileNotFoundError: If the path does not exist.
            PermissionError: If the path is not readable.
        """
        from datetime import datetime, timezone
        full = self._base() / path

        if full.is_dir():
            parts = []
            for md_file in sorted(full.rglob("*.md")):
                parts.append(
                    f"<!-- source: {md_file.relative_to(self._base())} -->\n"
                    + md_file.read_text(encoding="utf-8")
                )
            content = "\n\n---\n\n".join(parts) if parts else ""
        elif full.is_file():
            content = full.read_text(encoding="utf-8")
        else:
            raise FileNotFoundError(
                f"Grounding document not found: {full}\n"
                f"  base_path: {self._base()}\n"
                f"  path: {path}"
            )

        return DocContent(
            path=path,
            content=content,
            sha256=_sha256(content),
            fetched_at=datetime.now(tz=timezone.utc).isoformat(),
        )
