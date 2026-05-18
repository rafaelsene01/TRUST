"""Cache for external grounding sources (Notion, HTTP).

Stores fetched documents on disk with a configurable TTL. This avoids
hitting external APIs on every review run and ensures reviews are
reproducible within the TTL window.

Cache layout (under `<setup-repo>/.trust-cache/`):
    <source_id>/<path_hash>.json   ← per-document cache entry

Each entry is a JSON object:
    {
        "source_id": "...",
        "path": "...",
        "content": "...",
        "sha256": "...",
        "fetched_at": "<ISO-8601>",
        "expires_at": "<ISO-8601>"
    }

Volatile sources: entries are written but not used to gate HALT on hash
mismatch — their SHA is expected to change between runs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


DEFAULT_TTL_MINUTES = 60


@dataclass
class CacheEntry:
    source_id: str
    path: str
    content: str
    sha256: str
    fetched_at: str
    expires_at: str

    def is_expired(self) -> bool:
        try:
            expires = datetime.fromisoformat(self.expires_at)
            return datetime.now(tz=timezone.utc) >= expires
        except (ValueError, TypeError):
            return True


class SourceCache:
    """Disk-backed TTL cache for external grounding documents.

    Args:
        cache_dir:   Directory where cache files are stored.
        ttl_minutes: How long a cached entry is valid (default: 60).
    """

    def __init__(self, cache_dir: Path, ttl_minutes: int = DEFAULT_TTL_MINUTES):
        self.cache_dir = cache_dir
        self.ttl_minutes = ttl_minutes

    def _entry_path(self, source_id: str, doc_path: str) -> Path:
        key = hashlib.sha256(f"{source_id}:{doc_path}".encode()).hexdigest()[:16]
        source_slug = source_id.replace("/", "-").replace(":", "-")
        return self.cache_dir / source_slug / f"{key}.json"

    def get(self, source_id: str, doc_path: str) -> CacheEntry | None:
        """Return a valid (non-expired) cache entry, or None."""
        entry_path = self._entry_path(source_id, doc_path)
        if not entry_path.exists():
            return None
        try:
            data = json.loads(entry_path.read_text(encoding="utf-8"))
            entry = CacheEntry(**data)
            if entry.is_expired():
                entry_path.unlink(missing_ok=True)
                return None
            return entry
        except Exception:
            return None

    def put(self, source_id: str, doc_path: str, content: str, sha256: str) -> CacheEntry:
        """Store a document in the cache and return the entry."""
        now = datetime.now(tz=timezone.utc)
        expires = now + timedelta(minutes=self.ttl_minutes)
        entry = CacheEntry(
            source_id=source_id,
            path=doc_path,
            content=content,
            sha256=sha256,
            fetched_at=now.isoformat(),
            expires_at=expires.isoformat(),
        )
        entry_path = self._entry_path(source_id, doc_path)
        entry_path.parent.mkdir(parents=True, exist_ok=True)
        entry_path.write_text(json.dumps(asdict(entry), indent=2), encoding="utf-8")
        return entry

    def invalidate(self, source_id: str, doc_path: str) -> bool:
        """Remove a cache entry. Returns True if it existed."""
        entry_path = self._entry_path(source_id, doc_path)
        if entry_path.exists():
            entry_path.unlink()
            return True
        return False

    def clear_source(self, source_id: str) -> int:
        """Remove all cached entries for a source. Returns count removed."""
        source_slug = source_id.replace("/", "-").replace(":", "-")
        source_dir = self.cache_dir / source_slug
        if not source_dir.exists():
            return 0
        count = sum(1 for f in source_dir.glob("*.json"))
        import shutil
        shutil.rmtree(source_dir, ignore_errors=True)
        return count

    def stats(self) -> dict:
        """Return cache statistics."""
        total = 0
        expired = 0
        for entry_file in self.cache_dir.rglob("*.json"):
            total += 1
            try:
                data = json.loads(entry_file.read_text(encoding="utf-8"))
                entry = CacheEntry(**data)
                if entry.is_expired():
                    expired += 1
            except Exception:
                expired += 1
        return {
            "total_entries": total,
            "expired_entries": expired,
            "valid_entries": total - expired,
            "cache_dir": str(self.cache_dir),
            "ttl_minutes": self.ttl_minutes,
        }
