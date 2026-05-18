"""Spec file parser for TRUST Phase 6 — Rastreabilidade.

Parses `.spec.md` files that live in the ``specs/`` directory of the setup
repo. Each spec file has a YAML frontmatter block followed by the spec body
(requirements, acceptance criteria, etc.).

Typical file: ``specs/PAY-123.spec.md``

    ```markdown
    ---
    ticket_id: PAY-123
    title: "Add payment retry logic"
    type: story
    status: in-progress
    jira_url: https://empresa.atlassian.net/browse/PAY-123
    components:
      - payments
      - retry
    ---

    ## Summary
    Implement exponential-backoff retry for failed payment attempts.

    ## Acceptance Criteria
    - [ ] Given a failed payment, when retry is triggered, then it retries up to 3 times
    - [ ] Given all retries fail, then a DLQ event is emitted and ops is notified
    ```

The parser resolves spec files by:
  1. Exact filename match: ``specs/PAY-123.spec.md``
  2. Frontmatter ``ticket_id`` field scan across all ``.spec.md`` in spec_dir
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SpecFile:
    """Parsed spec file."""

    ticket_id: str
    title: str
    file_path: str                   # absolute path on disk
    content: str                     # full body (after frontmatter)
    acceptance_criteria: str         # extracted AC section
    spec_type: str = "story"         # story | task | bug | etc.
    status: str = "unknown"
    jira_url: str = ""
    components: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)


@dataclass
class SpecError:
    reason: str
    next_action: str


# ---------------------------------------------------------------------------
# YAML frontmatter helpers (stdlib only — no pyyaml dependency)
# ---------------------------------------------------------------------------


_FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (meta_dict, body)."""
    m = _FRONT_RE.match(text)
    if not m:
        return {}, text

    raw_yaml = m.group(1)
    body = text[m.end():]
    meta = _simple_yaml_parse(raw_yaml)
    return meta, body


def _simple_yaml_parse(raw: str) -> dict:
    """Parse simple YAML subset (str, list, inline values). No pyyaml."""
    result: dict = {}
    current_key: str | None = None
    in_list = False

    for line in raw.splitlines():
        # List item
        if line.startswith("  - ") or line.startswith("- "):
            item = line.lstrip("- ").strip().strip('"').strip("'")
            if current_key and in_list:
                result[current_key].append(item)
            continue

        # Key: value
        if ":" in line and not line.startswith(" "):
            key, _, raw_val = line.partition(":")
            key = key.strip()
            val = raw_val.strip().strip('"').strip("'")

            if val == "" or val == "|" or val == ">":
                # Possible list or block scalar follows
                result[key] = []
                current_key = key
                in_list = True
            else:
                result[key] = val
                current_key = key
                in_list = False
        else:
            in_list = False

    return result


# ---------------------------------------------------------------------------
# Acceptance criteria extraction
# ---------------------------------------------------------------------------


_AC_PATTERNS = [
    r"(?:##\s+)?(?:acceptance criteria|critérios de aceite|ac)[:\s]*\n(.*?)(?=\n##|\Z)",
    r"(?:##\s+)?(?:given|dado)[^\n]*\n(.*?)(?=\n##|\Z)",
]


def _extract_acceptance_criteria(body: str) -> str:
    for pat in _AC_PATTERNS:
        m = re.search(pat, body, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_spec_file(path: Path) -> SpecFile | SpecError:
    """Parse a single .spec.md file and return a SpecFile.

    Returns SpecError if the file doesn't exist or has no ticket_id.
    """
    if not path.exists():
        return SpecError(
            reason=f"Spec file not found: {path}",
            next_action=(
                f"Create the file at {path} using the template:\n"
                f"  cp ~/.trust/templates/spec.md.template {path}"
            ),
        )

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return SpecError(
            reason=f"Cannot read spec file {path}: {exc}",
            next_action="Check file permissions.",
        )

    meta, body = _parse_frontmatter(text)
    ticket_id = meta.get("ticket_id", "").upper().strip()
    if not ticket_id:
        return SpecError(
            reason=f"Spec file {path.name} has no 'ticket_id' in frontmatter.",
            next_action=(
                "Add 'ticket_id: PROJECT-NNN' to the YAML frontmatter block "
                "at the top of the file."
            ),
        )

    # Normalise components/labels — may be list or comma-separated string
    raw_components = meta.get("components", [])
    if isinstance(raw_components, str):
        raw_components = [c.strip() for c in raw_components.split(",") if c.strip()]
    elif not isinstance(raw_components, list):
        raw_components = []

    raw_labels = meta.get("labels", [])
    if isinstance(raw_labels, str):
        raw_labels = [l.strip() for l in raw_labels.split(",") if l.strip()]
    elif not isinstance(raw_labels, list):
        raw_labels = []

    return SpecFile(
        ticket_id=ticket_id,
        title=meta.get("title", "").strip('"').strip("'"),
        file_path=str(path.resolve()),
        content=body.strip(),
        acceptance_criteria=_extract_acceptance_criteria(body),
        spec_type=meta.get("type", "story"),
        status=meta.get("status", "unknown"),
        jira_url=meta.get("jira_url", ""),
        components=raw_components,
        labels=raw_labels,
    )


def find_spec_for_ticket(spec_dir: Path, ticket_id: str) -> SpecFile | None:
    """Search spec_dir for a spec file matching ticket_id.

    Search order:
    1. ``{spec_dir}/{ticket_id}.spec.md``  (canonical name)
    2. Any ``.spec.md`` file whose frontmatter ``ticket_id`` matches

    Returns None if not found.
    """
    if not spec_dir.is_dir():
        return None

    ticket_upper = ticket_id.upper()

    # 1. Canonical filename
    canonical = spec_dir / f"{ticket_upper}.spec.md"
    if canonical.exists():
        result = parse_spec_file(canonical)
        return result if isinstance(result, SpecFile) else None

    # 2. Frontmatter scan
    for spec_path in spec_dir.glob("*.spec.md"):
        result = parse_spec_file(spec_path)
        if isinstance(result, SpecFile) and result.ticket_id == ticket_upper:
            return result

    return None
