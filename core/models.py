"""Shared data models for the TRUST framework core."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PhaseStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    HALTED = "halted"
    SKIPPED = "skipped"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Verdict(str, Enum):
    COMPLIANT = "compliant"
    VIOLATION = "violation"
    NOT_APPLICABLE = "not_applicable"


# ---------------------------------------------------------------------------
# Diff models
# ---------------------------------------------------------------------------


@dataclass
class DiffHunk:
    hunk_id: str          # e.g. "src/auth/login.ts:42-58"
    file_path: str
    line_start: int
    line_end: int
    content: str          # raw hunk text


@dataclass
class DiffFile:
    path: str
    hunks: list[DiffHunk] = field(default_factory=list)
    full_content: str = ""


@dataclass
class Diff:
    branch: str
    base_branch: str
    files: list[DiffFile] = field(default_factory=list)

    def get_file(self, path: str) -> DiffFile | None:
        return next((f for f in self.files if f.path == path), None)

    def all_hunks(self) -> list[DiffHunk]:
        return [h for f in self.files for h in f.hunks]


# ---------------------------------------------------------------------------
# Grounding models
# ---------------------------------------------------------------------------


@dataclass
class GroundingDoc:
    source_id: str
    path: str
    content: str
    sha256: str
    bytes_read: int
    sections: list[str] = field(default_factory=list)   # heading anchors
    volatile: bool = False


@dataclass
class GroundingManifest:
    docs: list[GroundingDoc] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)

    @property
    def loaded(self) -> bool:
        return len(self.missing_required) == 0

    def total_bytes(self) -> int:
        return sum(d.bytes_read for d in self.docs)


# ---------------------------------------------------------------------------
# Finding models
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    agent: str
    rule_id: str
    rule_source: str
    file: str
    line_start: int
    line_end: int
    severity: Severity
    confidence: float
    claim: str
    evidence_quote: str
    why_it_matters: str
    suggestion: str
    false_positive_risk: str
    false_positive_reason: str | None


@dataclass
class CoverageVerdict:
    file: str
    verdict: Verdict
    reason: str | None = None    # required when NOT_APPLICABLE


@dataclass
class CoverageRule:
    rule_id: str
    title: str
    source: str
    verdicts: list[CoverageVerdict] = field(default_factory=list)


@dataclass
class CoverageMatrix:
    agent: str
    run_id: str
    rules_in_checklist_total: int
    diff_files_total: int
    files_in_domain_total: int
    files_in_domain_evaluated: int
    rules: list[CoverageRule] = field(default_factory=list)

    @property
    def rules_evaluated_total(self) -> int:
        return len(self.rules)

    @property
    def files_in_domain_evaluated_pct(self) -> float:
        if self.files_in_domain_total == 0:
            return 100.0
        return (self.files_in_domain_evaluated / self.files_in_domain_total) * 100

    @property
    def rules_evaluated_pct(self) -> float:
        if self.rules_in_checklist_total == 0:
            return 100.0
        return (self.rules_evaluated_total / self.rules_in_checklist_total) * 100


# ---------------------------------------------------------------------------
# Run models
# ---------------------------------------------------------------------------


@dataclass
class PhaseRecord:
    phase_id: int
    name: str
    status: PhaseStatus = PhaseStatus.PENDING
    started_at: str | None = None
    ended_at: str | None = None
    dod_passed: bool = False
    blocker: str | None = None
    artifact: str | None = None


@dataclass
class RunManifest:
    run_id: str
    branch: str
    target_id: str
    diff_sha: str
    started_at: str
    ended_at: str | None = None
    overall_status: str = "running"
    blocker: str | None = None
    phases: list[PhaseRecord] = field(default_factory=list)

    def get_phase(self, phase_id: int) -> PhaseRecord | None:
        return next((p for p in self.phases if p.phase_id == phase_id), None)

    def all_phases_done(self) -> bool:
        return all(p.status == PhaseStatus.DONE for p in self.phases)


# ---------------------------------------------------------------------------
# Config models
# ---------------------------------------------------------------------------


@dataclass
class SourceConfig:
    id: str
    adapter: str                  # "filesystem" | "notion" | "http"
    base_path: str | None = None
    base_url: str | None = None
    auth_env: str | None = None
    volatile: bool = False
    optional: bool = False
    cache_ttl_minutes: int = 60


@dataclass
class RequiredDoc:
    source: str
    path: str
    purpose: str = ""


@dataclass
class AgentConfig:
    id: str
    skill: str
    checklist: str
    file_patterns: list[str] = field(default_factory=lambda: ["**/*"])
    enabled: bool = True


@dataclass
class TrustConfig:
    framework_name: str
    version: str
    mode: str
    profile_type: str
    sources: list[SourceConfig] = field(default_factory=list)
    required_docs: list[RequiredDoc] = field(default_factory=list)
    agents: list[AgentConfig] = field(default_factory=list)
    confidence_threshold: float = 0.80
    runs_base_dir: str = "./runs"
    retention_policy: str = "audit_failures_only"
    raw: dict[str, Any] = field(default_factory=dict)

    def get_source(self, source_id: str) -> SourceConfig | None:
        return next((s for s in self.sources if s.id == source_id), None)

    def get_agent(self, agent_id: str) -> AgentConfig | None:
        return next((a for a in self.agents if a.id == agent_id), None)
