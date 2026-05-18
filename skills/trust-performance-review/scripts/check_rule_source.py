#!/usr/bin/env python3
"""Verifies that every rule_source in findings.json resolves to a real grounding section.

A rule_source that points to a non-existent anchor is a hallucination — the agent
claimed authority from a document that doesn't support that claim. This script
catches those before the meta-reviewer phase.

rule_source format: <source-id>:<path>#<anchor>
  e.g.: in-setup:06-security-policy.md#input-validation

The <anchor> is matched against Markdown headings in the grounding file,
normalized to lowercase with hyphens (GitHub-style anchor generation).

Usage:
    python check_rule_source.py <findings.json> <grounding-dir>

Exit codes:
    0  → all rule_sources resolve correctly
    1  → one or more rule_sources do not resolve
    2  → input files unreadable or malformed JSON
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


def _heading_to_anchor(heading: str) -> str:
    """Convert a Markdown heading text to a GitHub-style anchor.

    Lowercase, replace spaces with hyphens, strip non-alphanumeric chars
    (except hyphens).
    """
    heading = heading.lower()
    heading = re.sub(r"[^\w\s-]", "", heading)
    heading = re.sub(r"\s+", "-", heading.strip())
    return heading


def _extract_anchors(md_content: str) -> list[str]:
    """Extract all heading anchors from Markdown content."""
    anchors: list[str] = []
    for line in md_content.splitlines():
        m = re.match(r"^#{1,6}\s+(.+)$", line)
        if m:
            heading_text = m.group(1).strip()
            anchors.append(_heading_to_anchor(heading_text))
    return anchors


@dataclass
class SourceCheckResult:
    """Result of checking a single finding's rule_source."""

    rule_id: str
    file: str
    rule_source: str
    resolves: bool
    available_anchors: list[str] | None = None
    error_reason: str | None = None


def _load_findings(findings_path: Path) -> list[dict]:
    """Load and parse findings JSON."""
    try:
        raw = findings_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: findings not found: {findings_path}", file=sys.stderr)
        sys.exit(2)
    except PermissionError:
        print(f"Error: permission denied: {findings_path}", file=sys.stderr)
        sys.exit(2)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in findings: {exc}", file=sys.stderr)
        sys.exit(2)

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "findings" in data:
        return data["findings"]
    print("Error: findings.json must be a JSON array or {findings: [...]}", file=sys.stderr)
    sys.exit(2)


def _parse_rule_source(rule_source: str) -> tuple[str, str, str | None]:
    """Parse 'source-id:path#anchor' into (source_id, path, anchor_or_None)."""
    # Split off source-id prefix
    if ":" not in rule_source:
        raise ValueError(f"missing ':' in rule_source: {rule_source!r}")
    source_id, remainder = rule_source.split(":", 1)

    # Split path and optional anchor
    if "#" in remainder:
        path, anchor = remainder.split("#", 1)
    else:
        path, anchor = remainder, None

    return source_id, path, anchor


def check_rule_sources(
    findings: list[dict], grounding_dir: Path
) -> list[SourceCheckResult]:
    """Check every rule_source in findings against the grounding directory."""
    results: list[SourceCheckResult] = []

    for finding in findings:
        rule_id = finding.get("rule_id", "<unknown>")
        file_ = finding.get("file", "<unknown>")
        rule_source = finding.get("rule_source", "")

        if not rule_source:
            results.append(
                SourceCheckResult(
                    rule_id=rule_id,
                    file=file_,
                    rule_source=rule_source,
                    resolves=False,
                    error_reason="rule_source is empty",
                )
            )
            continue

        try:
            _source_id, path_str, anchor = _parse_rule_source(rule_source)
        except ValueError as exc:
            results.append(
                SourceCheckResult(
                    rule_id=rule_id,
                    file=file_,
                    rule_source=rule_source,
                    resolves=False,
                    error_reason=str(exc),
                )
            )
            continue

        # Find the file in grounding_dir (search recursively by filename)
        grounding_file = grounding_dir / path_str
        if not grounding_file.exists():
            # Try searching by basename only
            matches = list(grounding_dir.rglob(path_str))
            if matches:
                grounding_file = matches[0]
            else:
                results.append(
                    SourceCheckResult(
                        rule_id=rule_id,
                        file=file_,
                        rule_source=rule_source,
                        resolves=False,
                        error_reason=f"grounding file not found: {path_str!r}",
                    )
                )
                continue

        try:
            content = grounding_file.read_text(encoding="utf-8")
        except PermissionError:
            results.append(
                SourceCheckResult(
                    rule_id=rule_id,
                    file=file_,
                    rule_source=rule_source,
                    resolves=False,
                    error_reason=f"permission denied reading: {grounding_file}",
                )
            )
            continue

        available_anchors = _extract_anchors(content)

        # No anchor required — file existence is enough
        if anchor is None:
            results.append(
                SourceCheckResult(
                    rule_id=rule_id,
                    file=file_,
                    rule_source=rule_source,
                    resolves=True,
                )
            )
            continue

        # Normalize requested anchor
        normalized_anchor = _heading_to_anchor(anchor)
        if normalized_anchor in available_anchors:
            results.append(
                SourceCheckResult(
                    rule_id=rule_id,
                    file=file_,
                    rule_source=rule_source,
                    resolves=True,
                )
            )
        else:
            results.append(
                SourceCheckResult(
                    rule_id=rule_id,
                    file=file_,
                    rule_source=rule_source,
                    resolves=False,
                    available_anchors=available_anchors,
                    error_reason=f"anchor {anchor!r} not found in {grounding_file.name}",
                )
            )

    return results


def main() -> int:
    """CLI entry point."""
    if len(sys.argv) != 3:
        print(
            "Usage: check_rule_source.py <findings.json> <grounding-dir>",
            file=sys.stderr,
        )
        return 2

    findings_path = Path(sys.argv[1])
    grounding_dir = Path(sys.argv[2])

    if not grounding_dir.is_dir():
        print(f"Error: grounding-dir is not a directory: {grounding_dir}", file=sys.stderr)
        return 2

    findings = _load_findings(findings_path)

    if not findings:
        print("✓ No findings to check — rule_source check vacuously passes")
        return 0

    results = check_rule_sources(findings, grounding_dir)
    failures = [r for r in results if not r.resolves]

    if not failures:
        print(f"✓ All {len(results)} rule_source(s) resolve correctly")
        return 0

    print(
        f"✗ {len(failures)}/{len(results)} rule_source(s) do NOT resolve:",
        file=sys.stderr,
    )
    for r in failures:
        print(f"\n  finding: {r.rule_id} in {r.file}", file=sys.stderr)
        print(f"  rule_source: {r.rule_source!r}", file=sys.stderr)
        print(f"  reason: {r.error_reason}", file=sys.stderr)
        if r.available_anchors:
            anchors_preview = ", ".join(r.available_anchors[:8])
            if len(r.available_anchors) > 8:
                anchors_preview += f", ... ({len(r.available_anchors)} total)"
            print(f"  available anchors: {anchors_preview}", file=sys.stderr)

    return 1


if __name__ == "__main__":
    sys.exit(main())
