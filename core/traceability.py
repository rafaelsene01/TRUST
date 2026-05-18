"""Traceability orchestrator for TRUST Phase 6.

Resolves a branch name → Jira ticket ID → ticket metadata + spec file,
then annotates each finding with a ``traced_to`` block.

Usage (called by orchestrator._run_phase_6_traceability):

    result = run_traceability(
        branch="feat/PAY-123",
        findings=passed_findings,        # list[dict] from gate.report.json
        traceability_cfg=config.raw["traceability"],
        setup_path=setup_path,
    )
    if result.ok:
        # findings now have result.annotated_findings with traced_to
    else:
        # result.warning is a human-readable message (never raises)

Resolution strategy:
    1. Extract ticket_id from branch using branch_pattern (or default)
    2. Search spec_dir (if configured) for a matching .spec.md file
    3. If no spec file and Jira is configured → fetch from Jira API
    4. If nothing found → set traced_to = {"source": "not_found"}
    5. Annotate every finding with traced_to; return TraceabilityResult
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TracedTo:
    """Traceability annotation attached to each finding."""

    ticket_id: str
    title: str
    url: str
    source: str                      # "spec_file" | "jira" | "not_found"
    acceptance_criteria: str = ""
    status: str = ""
    components: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "acceptance_criteria": self.acceptance_criteria,
            "status": self.status,
            "components": self.components,
        }


@dataclass
class TraceabilityResult:
    """Output of run_traceability()."""

    ok: bool
    ticket_id: str | None
    traced_to: TracedTo | None
    annotated_findings: list[dict] = field(default_factory=list)
    warning: str | None = None        # set when ok=False; never raises


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_ticket_id(branch: str, cfg: dict) -> str | None:
    """Extract ticket ID from branch using config or default pattern."""
    from .jira_integration import extract_ticket_id
    pattern = cfg.get("branch_pattern")
    return extract_ticket_id(branch, pattern)


def _resolve_from_spec(
    ticket_id: str, spec_dir: Path
) -> TracedTo | None:
    """Try to resolve ticket info from a local spec file."""
    from .spec_parser import find_spec_for_ticket
    spec = find_spec_for_ticket(spec_dir, ticket_id)
    if spec is None:
        return None
    return TracedTo(
        ticket_id=spec.ticket_id,
        title=spec.title,
        url=spec.jira_url,
        source="spec_file",
        acceptance_criteria=spec.acceptance_criteria,
        status=spec.status,
        components=spec.components,
    )


def _resolve_from_jira(ticket_id: str, jira_cfg: dict) -> TracedTo | None:
    """Try to resolve ticket info from Jira API. Returns None on any error."""
    from .jira_integration import JiraClient, JiraError, JiraTicket

    base_url = jira_cfg.get("base_url", "").strip()
    if not base_url:
        return None

    auth = jira_cfg.get("auth", {})
    user_env = auth.get("user_env", "JIRA_USER")
    token_env = auth.get("token_env", "JIRA_TOKEN")

    client = JiraClient(base_url, user_env=user_env, token_env=token_env)
    result = client.get_ticket(ticket_id)

    if isinstance(result, JiraError):
        return None

    return TracedTo(
        ticket_id=result.ticket_id,
        title=result.summary,
        url=result.url,
        source="jira",
        acceptance_criteria=result.acceptance_criteria,
        status=result.status,
        components=result.components,
    )


def _annotate_findings(findings: list[dict], traced_to: TracedTo) -> list[dict]:
    """Return a copy of each finding with traced_to injected."""
    annotated = []
    for f in findings:
        copy = dict(f)
        copy["traced_to"] = traced_to.to_dict()
        annotated.append(copy)
    return annotated


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_traceability(
    branch: str,
    findings: list[dict],
    traceability_cfg: dict,
    setup_path: Path,
) -> TraceabilityResult:
    """Resolve traceability for the branch and annotate findings.

    Never raises. Errors are captured in TraceabilityResult.warning.

    Args:
        branch:           Feature branch name, e.g. 'feat/PAY-123'.
        findings:         Validated findings from Phase 5 (gate + meta-review).
        traceability_cfg: Raw ``traceability`` block from trust.config.yaml.
        setup_path:       Root of the TRUST setup repo.

    Returns:
        TraceabilityResult with ok, ticket_id, traced_to, annotated_findings.
    """
    # 1. Extract ticket ID
    ticket_id = _extract_ticket_id(branch, traceability_cfg)
    if not ticket_id:
        return TraceabilityResult(
            ok=False,
            ticket_id=None,
            traced_to=None,
            annotated_findings=list(findings),
            warning=(
                f"Could not extract a ticket ID from branch '{branch}'.\n"
                f"  Branch pattern: {traceability_cfg.get('branch_pattern', 'default')}\n"
                f"  Next action: rename the branch to include a ticket ID like PAY-123, "
                f"or adjust branch_pattern in trust.config.yaml."
            ),
        )

    traced_to: TracedTo | None = None

    # 2. Try local spec file first
    spec_dir_raw = traceability_cfg.get("spec_dir", "./specs")
    spec_dir = (setup_path / spec_dir_raw.lstrip("./")).resolve()

    try:
        traced_to = _resolve_from_spec(ticket_id, spec_dir)
    except Exception as exc:
        pass  # Spec dir errors are non-fatal; fall through to Jira

    # 3. Try Jira if no spec file
    if traced_to is None:
        jira_cfg = traceability_cfg.get("jira", {})
        if jira_cfg.get("base_url"):
            try:
                traced_to = _resolve_from_jira(ticket_id, jira_cfg)
            except Exception:
                pass  # Jira errors are non-fatal

    # 4. Fallback: ticket found in branch but no data resolved
    if traced_to is None:
        traced_to = TracedTo(
            ticket_id=ticket_id,
            title="",
            url="",
            source="not_found",
        )
        warning = (
            f"Ticket ID '{ticket_id}' extracted from branch, "
            f"but no spec file or Jira data found.\n"
            f"  Spec dir checked: {spec_dir}\n"
            f"  Next action: create {spec_dir}/{ticket_id}.spec.md "
            f"or configure Jira in trust.config.yaml."
        )
        return TraceabilityResult(
            ok=False,
            ticket_id=ticket_id,
            traced_to=traced_to,
            annotated_findings=_annotate_findings(findings, traced_to),
            warning=warning,
        )

    annotated = _annotate_findings(findings, traced_to)
    return TraceabilityResult(
        ok=True,
        ticket_id=ticket_id,
        traced_to=traced_to,
        annotated_findings=annotated,
    )
