#!/usr/bin/env python3
"""Validates that an agent's coverage.json has 100% rule × file evaluation.

This script enforces the Definition of Done for Phase 2 of the TRUST framework.
A coverage matrix is considered complete when:

  1. Every rule in the checklist appears in the coverage matrix
  2. Every (rule × file_in_domain) pair has a verdict
  3. Every "not_applicable" verdict has a non-empty justification

Usage:
    python validate_coverage.py <path-to-coverage.json>

Exit codes:
    0  → coverage is complete, agent may proceed
    1  → coverage is incomplete, HALT required
    2  → input file unreadable or malformed
    3  → schema violation in coverage.json

Example output (success):
    ✓ Coverage complete: 15/15 rules, 12/12 files in domain, 100%

Example output (failure):
    ✗ Coverage incomplete:
      - Rule SEC-012 not present in coverage matrix
      - File src/api/users.ts has no verdict for SEC-007
      - 2 not_applicable verdicts missing justification
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ValidationResult:
    """Outcome of validating a coverage.json."""

    ok: bool
    errors: list[str]
    summary: str

    @property
    def exit_code(self) -> int:
        return 0 if self.ok else 1


def validate_coverage(coverage_path: Path) -> ValidationResult:
    """Validate a coverage.json file.

    Returns a ValidationResult with ok=True only if the matrix is 100% complete.
    """
    # --- Step 1: load and parse ---
    try:
        raw = coverage_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ValidationResult(
            ok=False,
            errors=[f"File not found: {coverage_path}"],
            summary="cannot proceed",
        )
    except PermissionError:
        return ValidationResult(
            ok=False,
            errors=[f"Permission denied: {coverage_path}"],
            summary="cannot proceed",
        )

    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as e:
        return ValidationResult(
            ok=False,
            errors=[f"Invalid JSON: {e}"],
            summary="cannot proceed",
        )

    # --- Step 2: schema validation ---
    required_top_level = {
        "agent",
        "rules_in_checklist_total",
        "rules_evaluated_total",
        "diff_files_total",
        "files_in_domain_total",
        "files_in_domain_evaluated",
        "rules",
    }
    missing_keys = required_top_level - set(data.keys())
    if missing_keys:
        return ValidationResult(
            ok=False,
            errors=[f"Schema violation: missing keys {sorted(missing_keys)}"],
            summary="malformed coverage.json",
        )

    # --- Step 3: build the validation report ---
    errors: list[str] = []

    rules_in_checklist = data["rules_in_checklist_total"]
    rules_evaluated = data["rules_evaluated_total"]
    files_in_domain = data["files_in_domain_total"]
    files_evaluated = data["files_in_domain_evaluated"]

    # Rule count check
    if rules_evaluated < rules_in_checklist:
        missing = rules_in_checklist - rules_evaluated
        errors.append(
            f"Rules evaluated: {rules_evaluated}/{rules_in_checklist} "
            f"({missing} rules missing from coverage matrix)"
        )

    # File count check
    if files_evaluated < files_in_domain:
        missing = files_in_domain - files_evaluated
        errors.append(
            f"Files evaluated: {files_evaluated}/{files_in_domain} "
            f"({missing} files in domain not evaluated)"
        )

    # Per-rule × per-file verdict check
    rules: list[dict[str, Any]] = data.get("rules", [])
    if not rules:
        errors.append("Coverage matrix is empty: no rules listed")
    else:
        for rule in rules:
            rule_id = rule.get("rule_id", "<unknown>")
            verdicts = rule.get("verdicts", [])

            if not verdicts:
                errors.append(f"Rule {rule_id} has no verdicts (matrix incomplete)")
                continue

            # Check every N/A has justification
            for v in verdicts:
                if v.get("verdict") == "not_applicable":
                    reason = v.get("reason", "").strip()
                    if not reason:
                        errors.append(
                            f"Rule {rule_id} marked N/A for "
                            f"{v.get('file', '<unknown>')} without justification"
                        )

            # Check every verdict has a valid value
            valid_verdicts = {"compliant", "violation", "not_applicable"}
            for v in verdicts:
                verdict_value = v.get("verdict")
                if verdict_value not in valid_verdicts:
                    errors.append(
                        f"Rule {rule_id} has invalid verdict "
                        f"'{verdict_value}' for {v.get('file', '<unknown>')}"
                    )

    # --- Step 4: build summary ---
    if errors:
        summary = (
            f"✗ Coverage INCOMPLETE: "
            f"{rules_evaluated}/{rules_in_checklist} rules, "
            f"{files_evaluated}/{files_in_domain} files, "
            f"{len(errors)} error(s)"
        )
        return ValidationResult(ok=False, errors=errors, summary=summary)

    summary = (
        f"✓ Coverage complete: "
        f"{rules_evaluated}/{rules_in_checklist} rules, "
        f"{files_evaluated}/{files_in_domain} files in domain, 100%"
    )
    return ValidationResult(ok=True, errors=[], summary=summary)


def main() -> int:
    """CLI entry point."""
    if len(sys.argv) != 2:
        print(
            "Usage: validate_coverage.py <path-to-coverage.json>",
            file=sys.stderr,
        )
        return 2

    coverage_path = Path(sys.argv[1])
    result = validate_coverage(coverage_path)

    # Print summary
    print(result.summary)

    # Print errors if any
    if result.errors:
        print("\nErrors:", file=sys.stderr)
        for err in result.errors:
            print(f"  - {err}", file=sys.stderr)

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
