#!/usr/bin/env python3
"""Verifies that every evidence_quote in findings.json appears literally in the diff.

The TRUST framework requires evidence_quote to be a character-by-character copy
of the diff content. Paraphrasing is a hallucination and will be caught here
before the meta-reviewer ever sees it.

Usage:
    python check_evidence_literal.py <findings.json> <diff.patch>

Exit codes:
    0  → all evidence quotes found literally in diff
    1  → one or more quotes not found
    2  → input files unreadable or malformed JSON
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class QuoteCheckResult:
    """Result of checking a single finding's evidence_quote."""

    rule_id: str
    file: str
    quote: str
    found: bool
    nearest_hint: str | None = None


def _load_diff_content(diff_path: Path) -> str:
    """Read the entire diff as a single string."""
    try:
        return diff_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: diff not found: {diff_path}", file=sys.stderr)
        sys.exit(2)
    except PermissionError:
        print(f"Error: permission denied: {diff_path}", file=sys.stderr)
        sys.exit(2)


def _load_findings(findings_path: Path) -> list[dict]:
    """Load and parse the findings JSON file."""
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


def _nearest_diff_hint(quote: str, diff_content: str) -> str | None:
    """Find the closest substring in the diff to provide a diagnostic hint."""
    # Look for the first 20 chars of the quote as a starting anchor
    prefix = quote[:20].strip()
    if not prefix:
        return None
    idx = diff_content.find(prefix)
    if idx == -1:
        return None
    # Grab surrounding context (up to 80 chars)
    start = max(0, idx)
    snippet = diff_content[start : start + len(quote) + 10].replace("\n", "\\n")
    return f"nearest match starts at byte {idx}: {snippet!r}"


def check_evidence_quotes(
    findings: list[dict], diff_content: str
) -> list[QuoteCheckResult]:
    """Check every evidence_quote in findings against the diff content."""
    results: list[QuoteCheckResult] = []
    for finding in findings:
        rule_id = finding.get("rule_id", "<unknown>")
        file_ = finding.get("file", "<unknown>")
        quote = finding.get("evidence_quote", "")

        if not quote:
            results.append(
                QuoteCheckResult(
                    rule_id=rule_id,
                    file=file_,
                    quote=quote,
                    found=False,
                    nearest_hint="evidence_quote is empty",
                )
            )
            continue

        found = quote in diff_content
        hint = None if found else _nearest_diff_hint(quote, diff_content)
        results.append(
            QuoteCheckResult(
                rule_id=rule_id,
                file=file_,
                quote=quote,
                found=found,
                nearest_hint=hint,
            )
        )
    return results


def main() -> int:
    """CLI entry point."""
    if len(sys.argv) != 3:
        print(
            "Usage: check_evidence_literal.py <findings.json> <diff.patch>",
            file=sys.stderr,
        )
        return 2

    findings_path = Path(sys.argv[1])
    diff_path = Path(sys.argv[2])

    findings = _load_findings(findings_path)
    diff_content = _load_diff_content(diff_path)

    if not findings:
        print("✓ No findings to check — evidence check vacuously passes")
        return 0

    results = check_evidence_quotes(findings, diff_content)
    failures = [r for r in results if not r.found]

    if not failures:
        print(f"✓ All {len(results)} evidence quote(s) found literally in diff")
        return 0

    print(
        f"✗ {len(failures)}/{len(results)} evidence quote(s) NOT found in diff:",
        file=sys.stderr,
    )
    for r in failures:
        print(f"\n  finding: {r.rule_id} in {r.file}", file=sys.stderr)
        print(f"  quote:   {r.quote!r}", file=sys.stderr)
        if r.nearest_hint:
            print(f"  hint:    {r.nearest_hint}", file=sys.stderr)
        else:
            print("  hint:    no similar content found in diff", file=sys.stderr)

    return 1


if __name__ == "__main__":
    sys.exit(main())
