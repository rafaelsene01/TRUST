#!/usr/bin/env python3
"""Validates a security.dod.json attestation block produced by the security agent.

This is the final gate before the orchestrator advances to the next phase.
It confirms the agent filled every required field correctly and that no DoD
criterion was silently skipped.

Usage:
    python validate_dod_attestation.py <path-to-security.dod.json>

Exit codes:
    0  → attestation valid, self_check_passed: true
    1  → attestation FAILED (with details about every failed field)
    2  → file not found, unreadable, or invalid JSON
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _load(path: Path) -> dict:
    """Load and parse a JSON file."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except PermissionError:
        print(f"Error: permission denied: {path}", file=sys.stderr)
        sys.exit(2)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON: {exc}", file=sys.stderr)
        sys.exit(2)


def _check(
    errors: list[str],
    condition: bool,
    field: str,
    received,
    expected_desc: str,
) -> None:
    """Append an error if condition is False."""
    if not condition:
        errors.append(f"  - {field}: got {received!r}, expected {expected_desc}")


def validate_attestation(data: dict) -> list[str]:
    """Validate the attestation structure.

    Returns a list of error strings. Empty list means the attestation is valid.
    """
    errors: list[str] = []

    # Top-level required fields
    for field in ("agent", "agent_version", "run_id", "timestamp", "dod"):
        if field not in data:
            errors.append(f"  - missing top-level field: {field!r}")

    if errors:
        return errors  # Can't safely navigate missing keys

    dod = data.get("dod", {})
    if not isinstance(dod, dict):
        errors.append("  - 'dod' must be an object")
        return errors

    # --- grounding block ---
    grounding = dod.get("grounding", {})
    _check(errors, grounding.get("loaded") is True, "dod.grounding.loaded", grounding.get("loaded"), "true")

    missing_req = grounding.get("missing_required", None)
    if missing_req is None:
        errors.append("  - dod.grounding.missing_required: field missing")
    elif not isinstance(missing_req, list):
        errors.append(f"  - dod.grounding.missing_required: must be array, got {type(missing_req).__name__}")
    elif len(missing_req) > 0:
        errors.append(
            f"  - dod.grounding.missing_required: must be empty, "
            f"got {len(missing_req)} missing doc(s): {missing_req}"
        )

    docs_read = grounding.get("docs_read", None)
    if docs_read is None:
        errors.append("  - dod.grounding.docs_read: field missing")
    elif not isinstance(docs_read, list):
        errors.append("  - dod.grounding.docs_read: must be array")

    # --- checklist block ---
    checklist = dod.get("checklist", {})
    _check(errors, checklist.get("loaded") is True, "dod.checklist.loaded", checklist.get("loaded"), "true")

    total = checklist.get("rules_in_checklist_total")
    valid_src = checklist.get("rules_with_valid_source")
    if total is None:
        errors.append("  - dod.checklist.rules_in_checklist_total: field missing")
    if valid_src is None:
        errors.append("  - dod.checklist.rules_with_valid_source: field missing")
    if total is not None and valid_src is not None:
        _check(
            errors,
            valid_src == total,
            "dod.checklist.rules_with_valid_source",
            valid_src,
            f"{total} (= rules_in_checklist_total)",
        )

    # --- coverage block ---
    coverage = dod.get("coverage", {})
    for pct_field in ("files_in_domain_evaluated_pct", "rules_evaluated_pct", "not_applicable_with_justification_pct"):
        val = coverage.get(pct_field)
        if val is None:
            errors.append(f"  - dod.coverage.{pct_field}: field missing")
        else:
            _check(errors, val == 100, f"dod.coverage.{pct_field}", val, "100")

    matrix_complete = coverage.get("coverage_matrix_complete")
    if matrix_complete is None:
        errors.append("  - dod.coverage.coverage_matrix_complete: field missing")
    else:
        _check(errors, matrix_complete is True, "dod.coverage.coverage_matrix_complete", matrix_complete, "true")

    for count_field in ("diff_files_total", "files_in_domain_total", "files_in_domain_evaluated", "rules_evaluated_total"):
        if count_field not in coverage:
            errors.append(f"  - dod.coverage.{count_field}: field missing")

    # Consistency: evaluated must equal total
    total_files = coverage.get("files_in_domain_total")
    eval_files = coverage.get("files_in_domain_evaluated")
    if total_files is not None and eval_files is not None and eval_files != total_files:
        errors.append(
            f"  - dod.coverage.files_in_domain_evaluated: got {eval_files}, "
            f"expected {total_files} (= files_in_domain_total)"
        )

    # --- findings block ---
    findings = dod.get("findings", {})
    bool_fields = (
        "every_finding_has_rule_id",
        "every_finding_has_rule_source",
        "every_finding_has_evidence_quote",
        "every_finding_has_confidence",
        "every_finding_confidence_gte_080",
        "every_evidence_quote_literal",
    )
    for field in bool_fields:
        val = findings.get(field)
        if val is None:
            errors.append(f"  - dod.findings.{field}: field missing")
        else:
            _check(errors, val is True, f"dod.findings.{field}", val, "true")

    if "emitted" not in findings:
        errors.append("  - dod.findings.emitted: field missing")

    # --- top-level booleans ---
    self_check = dod.get("self_check_passed")
    halt = dod.get("halt_required")

    if self_check is None:
        errors.append("  - dod.self_check_passed: field missing")
    if halt is None:
        errors.append("  - dod.halt_required: field missing")

    # If no other errors, these must be consistent
    if not errors:
        if halt is not False:
            errors.append(f"  - dod.halt_required: got {halt!r}, expected false")
        if self_check is not True:
            errors.append(f"  - dod.self_check_passed: got {self_check!r}, expected true")

    return errors


def main() -> int:
    """CLI entry point."""
    if len(sys.argv) != 2:
        print(
            "Usage: validate_dod_attestation.py <path-to-security.dod.json>",
            file=sys.stderr,
        )
        return 2

    path = Path(sys.argv[1])
    data = _load(path)
    errors = validate_attestation(data)

    if not errors:
        print("✓ DoD attestation valid — self_check_passed: true")
        return 0

    print(f"✗ DoD attestation FAILED ({len(errors)} issue(s)):", file=sys.stderr)
    for err in errors:
        print(err, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
