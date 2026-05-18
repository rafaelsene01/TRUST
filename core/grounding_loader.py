"""Loads grounding documents from configured sources.

Phase 1 of the TRUST review pipeline.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .models import (
    GroundingDoc,
    GroundingManifest,
    RequiredDoc,
    SourceConfig,
    TrustConfig,
)


class GroundingError(Exception):
    """Raised when a required grounding document cannot be loaded."""


def _compute_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _extract_sections(content: str) -> list[str]:
    """Return list of heading anchors (GitHub-flavoured markdown)."""
    anchors = []
    for line in content.splitlines():
        if line.startswith("#"):
            heading = re.sub(r"^#+\s*", "", line).strip()
            anchor = re.sub(r"[^a-z0-9\s-]", "", heading.lower())
            anchor = re.sub(r"\s+", "-", anchor).strip("-")
            anchors.append(anchor)
    return anchors


def _load_from_notion(
    source: SourceConfig,
    doc_path: str,
    cache_dir: Path | None = None,
) -> GroundingDoc:
    """Load a document from the Notion adapter."""
    from adapters.notion_adapter import NotionAdapter
    from core.source_cache import SourceCache

    auth = getattr(source, "auth", {}) or {}
    token_env = auth.get("token_env", "NOTION_TOKEN")
    ttl = getattr(source, "cache_ttl_minutes", 60)

    cache = None
    if cache_dir is not None:
        cache = SourceCache(cache_dir, ttl_minutes=ttl)

    adapter = NotionAdapter(token_env=token_env, cache=cache, volatile=source.volatile)
    doc = adapter.read(doc_path, source_id=source.id)

    return GroundingDoc(
        source_id=source.id,
        path=doc_path,
        content=doc.content,
        sha256=doc.sha256,
        bytes_read=len(doc.content.encode("utf-8")),
        sections=_extract_sections(doc.content),
        volatile=source.volatile,
    )


def _load_from_http(
    source: SourceConfig,
    doc_path: str,
    cache_dir: Path | None = None,
) -> GroundingDoc:
    """Load a document from the HTTP adapter."""
    from adapters.http_adapter import HttpAdapter
    from core.source_cache import SourceCache

    auth = getattr(source, "auth", {}) or {}
    base_url = getattr(source, "base_url", "") or ""
    ttl = getattr(source, "cache_ttl_minutes", 60)

    cache = None
    if cache_dir is not None:
        cache = SourceCache(cache_dir, ttl_minutes=ttl)

    adapter = HttpAdapter(
        base_url=base_url,
        auth_config=auth,
        cache=cache,
        volatile=source.volatile,
    )
    doc = adapter.read(doc_path, source_id=source.id)

    return GroundingDoc(
        source_id=source.id,
        path=doc_path,
        content=doc.content,
        sha256=doc.sha256,
        bytes_read=len(doc.content.encode("utf-8")),
        sections=_extract_sections(doc.content),
        volatile=source.volatile,
    )


def _load_from_filesystem(
    source: SourceConfig,
    doc_path: str,
    setup_path: Path,
) -> GroundingDoc:
    """Load a document from the filesystem adapter."""
    base = source.base_path or ""

    # Resolve relative paths against the setup repo root
    if base.startswith("./") or not base.startswith("/"):
        resolved_base = setup_path / base
    else:
        resolved_base = Path(base)

    full_path = resolved_base / doc_path

    # Support directory paths — load all .md files inside
    if full_path.is_dir():
        parts = []
        for md_file in sorted(full_path.rglob("*.md")):
            parts.append(md_file.read_text(encoding="utf-8"))
        content = "\n\n---\n\n".join(parts) if parts else ""
    elif full_path.exists():
        content = full_path.read_text(encoding="utf-8")
    else:
        raise GroundingError(
            f"Required grounding doc not found: {full_path}\n"
            f"  source: {source.id}\n"
            f"  path:   {doc_path}\n"
            f"  Tip: run `/trust map codebase` to generate missing docs, "
            f"or create the file manually."
        )

    return GroundingDoc(
        source_id=source.id,
        path=doc_path,
        content=content,
        sha256=_compute_sha256(content),
        bytes_read=len(content.encode("utf-8")),
        sections=_extract_sections(content),
        volatile=source.volatile,
    )


def load_grounding(
    config: TrustConfig,
    setup_path: Path,
    cache_dir: Path | None = None,
) -> GroundingManifest:
    """Load all required grounding documents.

    Args:
        config:     Parsed TrustConfig with sources and required_docs.
        setup_path: Absolute path to the TRUST setup repo root.

    Returns:
        GroundingManifest with loaded docs.

    Raises:
        GroundingError: If any required (non-optional) doc cannot be loaded
                        and the framework is in strict mode.
    """
    manifest = GroundingManifest()

    for req in config.required_docs:
        source = config.get_source(req.source)

        if source is None:
            manifest.missing_required.append(
                f"{req.source}:{req.path} (source '{req.source}' not declared)"
            )
            continue

        try:
            if source.adapter == "filesystem":
                doc = _load_from_filesystem(source, req.path, setup_path)
            elif source.adapter == "notion":
                _cache_dir = cache_dir or (setup_path / ".trust-cache")
                doc = _load_from_notion(source, req.path, _cache_dir)
            elif source.adapter == "http":
                _cache_dir = cache_dir or (setup_path / ".trust-cache")
                doc = _load_from_http(source, req.path, _cache_dir)
            else:
                raise GroundingError(
                    f"Unknown adapter '{source.adapter}'. "
                    f"Supported: 'filesystem', 'notion', 'http'.\n"
                    f"  Next action: fix adapter value in trust.config.yaml"
                )

            # Sanity check: docs that are too small are likely stubs
            if not source.volatile and doc.bytes_read < 200:
                print(
                    f"  ⚠ Warning: {req.source}:{req.path} is very small "
                    f"({doc.bytes_read} bytes). "
                    f"Is it a draft or placeholder?"
                )

            manifest.docs.append(doc)

        except GroundingError as e:
            if source.optional:
                print(f"  ⏭  Optional source skipped: {req.source}:{req.path}")
            else:
                manifest.missing_required.append(str(e))

    return manifest


def validate_grounding_dod(
    manifest: GroundingManifest,
    min_total_bytes: int = 5000,
    previous_sha_map: dict[str, str] | None = None,
) -> tuple[bool, list[str]]:
    """Validate the Definition of Done for Phase 1.

    Args:
        manifest:         Loaded grounding manifest.
        min_total_bytes:  Minimum total bytes across all docs.
        previous_sha_map: Optional dict of {source_id:path -> sha256} from a
                          previous run. Non-volatile sources that changed will
                          emit a warning (not an error — intentional edits are fine).
                          Volatile sources never trigger errors on hash mismatch.

    Returns:
        (ok, errors) — ok is True only if all DoD criteria pass.
    """
    errors: list[str] = []

    if manifest.missing_required:
        for missing in manifest.missing_required:
            errors.append(f"Missing required doc: {missing}")

    total_bytes = manifest.total_bytes()
    if total_bytes < min_total_bytes:
        errors.append(
            f"Total grounding size too small: {total_bytes} bytes "
            f"(minimum: {min_total_bytes}). "
            f"Grounding docs look like stubs."
        )

    if not manifest.docs:
        errors.append("No grounding documents loaded at all.")

    # Volatile sources: warn on hash change, never error
    if previous_sha_map:
        for doc in manifest.docs:
            key = f"{doc.source_id}:{doc.path}"
            prev_sha = previous_sha_map.get(key)
            if prev_sha and prev_sha != doc.sha256:
                if doc.volatile:
                    print(
                        f"  ℹ  Volatile source changed: {key} "
                        f"(sha changed — expected for Notion/HTTP sources)"
                    )
                else:
                    print(
                        f"  ⚠  Non-volatile source changed: {key} "
                        f"(sha changed since last run — intentional?)"
                    )

    return len(errors) == 0, errors
