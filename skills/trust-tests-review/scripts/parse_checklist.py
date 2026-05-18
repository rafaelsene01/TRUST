#!/usr/bin/env python3
"""Parses security.checklist.md into structured JSON.

The TRUST orchestrator and agents need a machine-readable representation of the
checklist. This script is the single source of truth for that parsing — every
execution uses the same deterministic algorithm.

Usage:
    python parse_checklist.py <path-to-checklist.md> [--output <path.json>]

    Without --output, prints JSON to stdout.

Exit codes:
    0  → parsed successfully; JSON written to stdout or file
    1  → one or more rules are malformed (with actionable error message)
    2  → file not found or unreadable
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


_RULE_HEADER_RE = re.compile(r"^###\s+([A-Z]+-\d{3})\s+—\s+(.+)$")
_SOURCE_RE = re.compile(r"\*\*Source:\*\*\s+`([^`]+)`")
_SEVERITY_RE = re.compile(r"\*\*Severity default:\*\*\s+(\w+)")
_APPLIES_RE = re.compile(r"\*\*Applies to:\*\*\s+(.+)$")
_VALID_SEVERITIES = {"critical", "high", "medium", "low"}


@dataclass
class Rule:
    """Structured representation of a checklist rule."""

    rule_id: str
    title: str
    source: str
    severity_default: str
    applies_to: str


def _validate_source(source: str, rule_id: str) -> str | None:
    """Return error message if source is invalid, else None."""
    if "#" not in source:
        return (
            f"{rule_id}: source must include a section anchor "
            f"(e.g. '06-security-policy.md#input-validation'), got: {source!r}"
        )
    return None


def parse_checklist(md_content: str) -> tuple[list[Rule], list[str]]:
    """Parse a checklist Markdown string into a list of Rules.

    Returns (rules, errors). errors is empty on success.
    """
    rules: list[Rule] = []
    errors: list[str] = []

    current_rule_id: str | None = None
    current_title: str | None = None
    current_source: str | None = None
    current_severity: str | None = None
    current_applies: str | None = None

    def _flush() -> None:
        """Finalize the current rule being parsed."""
        if current_rule_id is None:
            return

        local_errors: list[str] = []
        if not current_title:
            local_errors.append(f"{current_rule_id}: missing title")
        if not current_source:
            local_errors.append(f"{current_rule_id}: missing Source field")
        else:
            err = _validate_source(current_source, current_rule_id)
            if err:
                local_errors.append(err)
        if not current_severity:
            local_errors.append(f"{current_rule_id}: missing 'Severity default'")
        elif current_severity not in _VALID_SEVERITIES:
            local_errors.append(
                f"{current_rule_id}: invalid severity {current_severity!r}; "
                f"must be one of {sorted(_VALID_SEVERITIES)}"
            )

        if local_errors:
            errors.extend(local_errors)
        else:
            rules.append(
                Rule(
                    rule_id=current_rule_id,
                    title=current_title,  # type: ignore[arg-type]
                    source=current_source,  # type: ignore[arg-type]
                    severity_default=current_severity,  # type: ignore[arg-type]
                    applies_to=current_applies or "all files",
                )
            )

    for line in md_content.splitlines():
        header_match = _RULE_HEADER_RE.match(line)
        if header_match:
            _flush()
            current_rule_id = header_match.group(1)
            current_title = header_match.group(2).strip()
            current_source = None
            current_severity = None
            current_applies = None
            continue

        if current_rule_id is None:
            continue

        source_match = _SOURCE_RE.search(line)
        if source_match:
            current_source = source_match.group(1).strip()

        severity_match = _SEVERITY_RE.search(line)
        if severity_match:
            current_severity = severity_match.group(1).strip().lower()

        applies_match = _APPLIES_RE.search(line)
        if applies_match:
            current_applies = applies_match.group(1).strip()

    _flush()
    return rules, errors


def main() -> int:
    """CLI entry point."""
    args = sys.argv[1:]
    output_path: Path | None = None

    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 >= len(args):
            print("Error: --output requires a path argument", file=sys.stderr)
            return 2
        output_path = Path(args[idx + 1])
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]

    if len(args) != 1:
        print(
            "Usage: parse_checklist.py <path-to-checklist.md> [--output <path.json>]",
            file=sys.stderr,
        )
        return 2

    checklist_path = Path(args[0])
    try:
        content = checklist_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: file not found: {checklist_path}", file=sys.stderr)
        return 2
    except PermissionError:
        print(f"Error: permission denied: {checklist_path}", file=sys.stderr)
        return 2

    rules, errors = parse_checklist(content)

    if errors:
        print(f"✗ Checklist has {len(errors)} malformed rule(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    output = {
        "total": len(rules),
        "rules": [asdict(r) for r in rules],
    }
    serialized = json.dumps(output, indent=2, ensure_ascii=False)

    if output_path:
        output_path.write_text(serialized, encoding="utf-8")
        print(f"✓ {len(rules)} rule(s) parsed → {output_path}")
    else:
        print(serialized)

    return 0


if __name__ == "__main__":
    sys.exit(main())
