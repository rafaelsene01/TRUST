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
            else:
                # Adapters for notion/http are v1.1+
                raise GroundingError(
                    f"Adapter '{source.adapter}' is not available in this version. "
                    f"Only 'filesystem' is supported in MVP. "
                    f"Notion and HTTP adapters land in v1.1."
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
) -> tuple[bool, list[str]]:
    """Validate the Definition of Done for Phase 1.

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

    return len(errors) == 0, errors
