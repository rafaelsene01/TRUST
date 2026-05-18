"""TRUST orchestrator — drives the 8-phase review pipeline.

This is the brain of the framework. It:
  1. Resolves the setup repo and target
  2. Captures the diff
  3. Drives each phase in sequence, enforcing DoD
  4. HALTs on any failure in strict mode
  5. Cleans up or preserves artifacts based on retention policy
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .config_loader import ConfigError, load_config
from .grounding_loader import GroundingManifest, load_grounding, validate_grounding_dod
from .halt_handler import HaltError, trigger_halt
from .models import RunManifest, TrustConfig
from .run_manifest import (
    create_manifest,
    finalise_manifest,
    mark_phase_done,
    mark_phase_skipped,
    mark_phase_start,
    save_manifest,
)


# ---------------------------------------------------------------------------
# Setup resolution
# ---------------------------------------------------------------------------


class SetupError(Exception):
    """Raised when the TRUST setup cannot be resolved."""


def resolve_setup_path() -> Path:
    """Resolve the TRUST setup repo path from the environment.

    Reads TRUST_SETUP_PATH env var. Raises SetupError if not set or invalid.
    """
    import os
    raw = os.environ.get("TRUST_SETUP_PATH", "").strip()
    if not raw:
        raise SetupError(
            "TRUST_SETUP_PATH is not set.\n"
            "  Add it to your shell:\n"
            "    export TRUST_SETUP_PATH=~/work/your-team-trust\n"
            "  Then run /trust doctor to verify everything is connected."
        )
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise SetupError(
            f"TRUST_SETUP_PATH points to a directory that does not exist:\n"
            f"  {path}\n"
            f"  Check the path or re-run /trust init pilot."
        )
    return path


def resolve_target(setup_path: Path, cwd: Path) -> dict:
    """Find the target.yaml that matches the current repo's git remote."""
    targets_dir = setup_path / "targets"
    if not targets_dir.exists():
        raise SetupError(
            f"No targets/ directory found in setup repo at {setup_path}.\n"
            f"Run /trust target add <path-to-product-repo> to add a target."
        )

    # Get current repo's git remote URL
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=cwd,
            check=True,
        )
        current_remote = result.stdout.strip()
    except subprocess.CalledProcessError:
        current_remote = ""

    import yaml
    for yaml_file in targets_dir.glob("*.yaml"):
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            target = data.get("target", {})
            if current_remote and target.get("remote_url") == current_remote:
                return data
            # Fallback: match by repo_path
            import os
            repo_path_raw = target.get("repo_path", "")
            repo_path = Path(
                repo_path_raw.replace("${", "").replace("}", "")
            ).expanduser()
            if repo_path.resolve() == cwd.resolve():
                return data
        except Exception:
            continue

    # If no match, return a minimal default target using the first .yaml found
    yamls = list(targets_dir.glob("*.yaml"))
    if yamls:
        import yaml as _yaml
        data = _yaml.safe_load(yamls[0].read_text(encoding="utf-8"))
        if isinstance(data, dict):
            print(
                f"  ⚠  No exact target match found. "
                f"Using: {yamls[0].name}"
            )
            return data

    raise SetupError(
        f"No matching target found for this repo.\n"
        f"  git remote: {current_remote or '(none)'}\n"
        f"  cwd: {cwd}\n"
        f"  Add a target with: /trust target add {cwd}"
    )


# ---------------------------------------------------------------------------
# Diff capture
# ---------------------------------------------------------------------------


def capture_diff(base_branch: str, feature_branch: str, cwd: Path) -> str:
    """Run git diff and return the unified diff as a string."""
    try:
        result = subprocess.run(
            ["git", "diff", f"{base_branch}...{feature_branch}"],
            capture_output=True,
            text=True,
            cwd=cwd,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise SetupError(
            f"Failed to capture git diff:\n  {e.stderr}\n"
            f"  Make sure both branches exist: {base_branch} and {feature_branch}"
        ) from e


def parse_diff(diff_text: str) -> list[dict]:
    """Parse unified diff into a list of file dicts."""
    files: list[dict] = []
    current_file: dict | None = None

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            if current_file:
                files.append(current_file)
            current_file = {"path": "", "hunks": [], "content_lines": []}
        elif line.startswith("+++ b/") and current_file is not None:
            current_file["path"] = line[6:]
        elif current_file is not None:
            current_file["content_lines"].append(line)

    if current_file:
        files.append(current_file)

    return files


# ---------------------------------------------------------------------------
# Phase runners
# ---------------------------------------------------------------------------


def _run_phase_0_trigger(
    manifest: RunManifest,
    run_dir: Path,
    diff_text: str,
    diff_files: list[dict],
) -> None:
    """Phase 0: Trigger — write diff summary to run dir."""
    phase = mark_phase_start(manifest, 0, run_dir)

    # Persist diff to run dir for agents to read
    (run_dir / "diff.patch").write_text(diff_text, encoding="utf-8")
    summary = {
        "files_total": len(diff_files),
        "files": [f["path"] for f in diff_files],
        "hunks_total": sum(len(f["hunks"]) for f in diff_files),
    }
    (run_dir / "diff-summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    mark_phase_done(manifest, phase, run_dir, artifact="diff.patch")
    print(
        f"  ✅ Phase 0 done: {summary['files_total']} files, "
        f"{summary['hunks_total']} hunks"
    )


def _run_phase_1_grounding(
    manifest: RunManifest,
    run_dir: Path,
    config: TrustConfig,
    setup_path: Path,
) -> GroundingManifest:
    """Phase 1: Grounding — load and validate project docs."""
    phase = mark_phase_start(manifest, 1, run_dir)

    grounding = load_grounding(config, setup_path)
    ok, errors = validate_grounding_dod(grounding)

    if not ok:
        trigger_halt(
            manifest,
            phase,
            blocker="Grounding DoD failed — required docs missing or too small",
            run_dir=run_dir,
            errors=errors,
        )

    # Persist manifest to run dir
    manifest_data = {
        "docs": [
            {
                "source_id": d.source_id,
                "path": d.path,
                "sha256": d.sha256,
                "bytes_read": d.bytes_read,
                "sections_count": len(d.sections),
                "volatile": d.volatile,
            }
            for d in grounding.docs
        ],
        "total_bytes": grounding.total_bytes(),
        "missing_required": grounding.missing_required,
    }
    artifact = "grounding.manifest.json"
    (run_dir / artifact).write_text(
        json.dumps(manifest_data, indent=2), encoding="utf-8"
    )

    mark_phase_done(manifest, phase, run_dir, artifact=artifact)
    print(
        f"  ✅ Phase 1 done: {len(grounding.docs)} docs loaded "
        f"({grounding.total_bytes():,} bytes)"
    )
    return grounding


def _run_phase_4_precision_gate(
    manifest: RunManifest,
    run_dir: Path,
    threshold: float,
    agents_dir: Path,
) -> None:
    """Phase 4: Precision Gate — filter findings by confidence threshold."""
    phase = mark_phase_start(manifest, 4, run_dir)

    all_findings: list[dict] = []
    for findings_file in agents_dir.glob("*.findings.json"):
        try:
            data = json.loads(findings_file.read_text(encoding="utf-8"))
            findings = data if isinstance(data, list) else data.get("findings", [])
            all_findings.extend(findings)
        except (json.JSONDecodeError, OSError):
            continue

    passed = [f for f in all_findings if f.get("confidence", 0) >= threshold]
    silenced = [f for f in all_findings if f.get("confidence", 0) < threshold]

    gate_report = {
        "threshold": threshold,
        "findings_in": len(all_findings),
        "findings_passed": len(passed),
        "findings_silenced": len(silenced),
        "passed": passed,
        "silenced": silenced,
    }
    artifact = "gate.report.json"
    (run_dir / artifact).write_text(
        json.dumps(gate_report, indent=2), encoding="utf-8"
    )

    mark_phase_done(manifest, phase, run_dir, artifact=artifact)
    print(
        f"  ✅ Phase 4 done: {len(passed)} findings passed, "
        f"{len(silenced)} silenced (confidence < {threshold})"
    )


def _run_phase_6_traceability_skip(
    manifest: RunManifest,
    run_dir: Path,
) -> None:
    """Phase 6: Traceability — skip when not configured."""
    phase = mark_phase_start(manifest, 6, run_dir)
    skip_data = {"skipped": True, "reason": "traceability.enabled: false in config"}
    (run_dir / "traceability.json").write_text(
        json.dumps(skip_data, indent=2), encoding="utf-8"
    )
    mark_phase_skipped(manifest, phase, run_dir, reason="traceability disabled")
    print("  ⏭  Phase 6 skipped: traceability not configured")


def _run_phase_6_traceability(
    manifest: RunManifest,
    run_dir: Path,
    branch: str,
    findings: list[dict],
    traceability_cfg: dict,
    setup_path: Path,
) -> list[dict]:
    """Phase 6: Traceability — resolve ticket and annotate findings."""
    from .traceability import run_traceability

    phase = mark_phase_start(manifest, 6, run_dir)

    result = run_traceability(
        branch=branch,
        findings=findings,
        traceability_cfg=traceability_cfg,
        setup_path=setup_path,
    )

    report: dict = {
        "skipped": False,
        "ok": result.ok,
        "ticket_id": result.ticket_id,
        "traced_to": result.traced_to.to_dict() if result.traced_to else None,
        "warning": result.warning,
    }
    (run_dir / "traceability.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    if result.ok:
        mark_phase_done(manifest, phase, run_dir, artifact="traceability.json")
        t = result.traced_to
        assert t is not None
        print(
            f"  ✅ Phase 6 done: {t.ticket_id} — {t.title!r} "
            f"[{t.source}]"
        )
    else:
        mark_phase_skipped(manifest, phase, run_dir, reason=result.warning or "not resolved")
        print(f"  ⚠  Phase 6 warning: {result.warning}")

    return result.annotated_findings


def _run_phase_7_output(
    manifest: RunManifest,
    run_dir: Path,
    branch: str,
    output_path: Path,
    traceability_report: dict | None = None,
) -> Path:
    """Phase 7: Output — assemble final REVIEW.md."""
    phase = mark_phase_start(manifest, 7, run_dir)

    gate_file = run_dir / "gate.report.json"
    if gate_file.exists():
        gate = json.loads(gate_file.read_text(encoding="utf-8"))
        passed = gate.get("passed", [])
        silenced = gate.get("silenced", [])
    else:
        passed, silenced = [], []

    meta_file = run_dir / "meta-review.json"
    hallucinations = []
    hallucinations_count = 0
    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        hallucinations = meta.get("hallucinations_caught_detail", [])
        hallucinations_count = meta.get("hallucinations_caught", 0)

    # Group by severity
    severity_order = ["critical", "high", "medium", "low"]
    grouped: dict[str, list] = {s: [] for s in severity_order}
    for f in passed:
        sev = f.get("severity", "low")
        grouped.setdefault(sev, []).append(f)

    lines = [
        f"# TRUST Review — `{branch}`",
        f"\n> **Run ID:** `{manifest.run_id}`",
        f"> **Target:** `{manifest.target_id}`",
    ]

    # Traceability block (when resolved)
    if traceability_report and not traceability_report.get("skipped"):
        traced = traceability_report.get("traced_to")
        if traced and traced.get("source") not in (None, "not_found"):
            ticket_id = traced.get("ticket_id", "")
            ticket_title = traced.get("title", "")
            ticket_url = traced.get("url", "")
            ticket_status = traced.get("status", "")
            ticket_components = ", ".join(traced.get("components", []))
            ac = traced.get("acceptance_criteria", "")
            source = traced.get("source", "")

            url_part = f" — [{ticket_id}]({ticket_url})" if ticket_url else f" — {ticket_id}"
            lines += [
                f"> **Ticket:**{url_part} {ticket_title}",
                f"> **Status:** {ticket_status}" + (
                    f"  **Components:** {ticket_components}" if ticket_components else ""
                ),
                f"> **Source:** `{source}`",
            ]
            if ac:
                lines += [
                    "",
                    "<details>",
                    "<summary>📋 Acceptance Criteria</summary>",
                    "",
                    ac,
                    "",
                    "</details>",
                ]
        elif traceability_report.get("warning"):
            lines.append(
                f"\n> ⚠️  **Rastreabilidade:** {traceability_report['warning']}"
            )

    lines += [
        "\n---",
        "\n⚠️  **The AI never approves or rejects this PR. All decisions are yours.**",
        "\n---\n",
    ]

    # Summary table
    lines += [
        "## Summary",
        "",
        f"| Critical | High | Medium | Low | Silenced | Hallucinations intercepted |",
        f"| --- | --- | --- | --- | --- | --- |",
        f"| {len(grouped['critical'])} | {len(grouped['high'])} | "
        f"{len(grouped['medium'])} | {len(grouped['low'])} | "
        f"{len(silenced)} | {hallucinations_count} |",
        "",
    ]

    if not passed:
        lines.append("✅ No findings above the confidence threshold.")
    else:
        lines.append("## Findings\n")
        for severity in severity_order:
            findings = grouped[severity]
            if not findings:
                continue
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}
            lines.append(f"### {emoji.get(severity, '')} {severity.capitalize()}\n")
            for i, f in enumerate(findings, 1):
                lines += [
                    f"#### [{f.get('rule_id', '?')}] {f.get('claim', '')}",
                    f"",
                    f"**File:** `{f.get('file', '')}` "
                    f"(line {f.get('line_start', '?')}–{f.get('line_end', '?')})",
                    f"**Confidence:** {f.get('confidence', 0):.0%}  "
                    f"**False-positive risk:** {f.get('false_positive_risk', '?')}",
                    f"",
                    f"```",
                    f"{f.get('evidence_quote', '')}",
                    f"```",
                    f"",
                    f"**Why it matters:** {f.get('why_it_matters', '')}",
                    f"",
                    f"**Suggestion:** {f.get('suggestion', '')}",
                    f"",
                    f"> Rule source: `{f.get('rule_source', '')}`",
                    "",
                ]

    # Silenced appendix
    if silenced:
        lines += [
            "\n---\n",
            "<details>",
            f"<summary>🔇 Silenced findings ({len(silenced)}) — "
            f"confidence below threshold</summary>\n",
        ]
        for f in silenced:
            lines.append(
                f"- `{f.get('rule_id', '?')}` in `{f.get('file', '?')}` "
                f"— confidence {f.get('confidence', 0):.0%}"
            )
        lines.append("</details>")

    # Hallucinations appendix
    if hallucinations:
        lines += [
            "\n<details>",
            f"<summary>👻 Intercepted hallucinations ({len(hallucinations)})</summary>\n",
        ]
        for h in hallucinations:
            lines.append(
                f"- `{h.get('rule_id', '?')}` in `{h.get('file', '?')}` "
                f"— {h.get('rejection_reason', 'unknown reason')}"
            )
        lines.append("</details>")

    review_md = "\n".join(lines)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(review_md, encoding="utf-8")

    # Also write to run_dir for audit
    (run_dir / "REVIEW.md").write_text(review_md, encoding="utf-8")

    mark_phase_done(manifest, phase, run_dir, artifact="REVIEW.md")
    print(f"  ✅ Phase 7 done: REVIEW.md written to {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def cleanup_run(run_dir: Path, retention_policy: str) -> None:
    """Remove intermediate artifacts per the retention policy."""
    if retention_policy == "all_versioned":
        return  # keep everything

    if retention_policy == "ephemeral":
        import shutil
        shutil.rmtree(run_dir, ignore_errors=True)
        return

    if retention_policy in ("audit_failures_only", "gitignored"):
        # Keep only REVIEW.md, remove JSON artifacts
        for f in run_dir.glob("*.json"):
            f.unlink(missing_ok=True)
        agents_dir = run_dir / "agents"
        if agents_dir.exists():
            import shutil
            shutil.rmtree(agents_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_review(
    feature_branch: str,
    base_branch: str = "main",
    cwd: Path | None = None,
) -> Path:
    """Run the full TRUST review pipeline.

    Args:
        feature_branch: Branch to review (e.g. 'feat/PAY-123')
        base_branch:    Branch to diff against (default: 'main')
        cwd:            Working directory (default: current dir)

    Returns:
        Path to the generated REVIEW.md.

    Raises:
        SetupError: If setup/target cannot be resolved.
        ConfigError: If trust.config.yaml is invalid.
        HaltError: If any phase fails its DoD in strict mode.
    """
    import os
    if cwd is None:
        cwd = Path.cwd()

    print(f"\n🚀 TRUST review starting")
    print(f"   branch: {feature_branch}")
    print(f"   base:   {base_branch}\n")

    # --- Resolve setup ---
    setup_path = resolve_setup_path()
    config = load_config(setup_path)
    target_data = resolve_target(setup_path, cwd)
    target_id = target_data.get("target", {}).get("id", "unknown")

    print(f"   setup:  {setup_path}")
    print(f"   target: {target_id}\n")

    # --- Capture diff ---
    diff_text = capture_diff(base_branch, feature_branch, cwd)
    diff_files = parse_diff(diff_text)

    # --- Create run manifest ---
    runs_dir = setup_path / config.runs_base_dir.lstrip("./")
    manifest, run_dir = create_manifest(feature_branch, target_id, diff_text, runs_dir)

    print(f"   run-id: {manifest.run_id}")
    print(f"   run-dir: {run_dir}\n")

    try:
        # --- Phase 0: Trigger ---
        _run_phase_0_trigger(manifest, run_dir, diff_text, diff_files)

        # --- Phase 1: Grounding ---
        grounding = _run_phase_1_grounding(manifest, run_dir, config, setup_path)

        # --- Phase 2 & 3: Agent execution (driven by Claude via slash command) ---
        # The orchestrator writes a prompt file for the security agent.
        # In MVP, the agent is invoked by the /trust review-pr slash command
        # which reads this file and calls the skill.
        phase2 = mark_phase_start(manifest, 2, run_dir)
        agents_dir = run_dir / "agents"
        agents_dir.mkdir(exist_ok=True)

        # Write agent context file for Claude to pick up
        agent_context = {
            "run_id": manifest.run_id,
            "run_dir": str(run_dir),
            "agents_dir": str(agents_dir),
            "diff_patch": str(run_dir / "diff.patch"),
            "grounding_manifest": str(run_dir / "grounding.manifest.json"),
            "setup_path": str(setup_path),
            "agents_to_run": [
                {
                    "id": a.id,
                    "skill": a.skill,
                    "checklist": str(setup_path / a.checklist.lstrip("./")),
                    "enabled": a.enabled,
                }
                for a in config.agents
                if a.enabled
            ],
            "confidence_threshold": config.confidence_threshold,
        }
        ctx_file = run_dir / "agent-context.json"
        ctx_file.write_text(json.dumps(agent_context, indent=2), encoding="utf-8")

        # Phase 2 completes when agents write their findings.json files
        # This is signalled by the slash command after Claude finishes
        # For MVP: check if findings already exist (re-run scenario)
        if any(agents_dir.glob("*.findings.json")):
            mark_phase_done(manifest, phase2, run_dir, artifact="agents/")
            print(f"  ✅ Phase 2: agent findings found")

            phase3 = mark_phase_start(manifest, 3, run_dir)
            if any(agents_dir.glob("*.second-pass.json")):
                mark_phase_done(manifest, phase3, run_dir, artifact="agents/")
                print(f"  ✅ Phase 3: second pass found")
            else:
                print(f"  ⏭  Phase 3: second pass not yet run (MVP — optional)")
                mark_phase_skipped(manifest, phase3, run_dir, "MVP: second pass skipped")
        else:
            print(f"\n  📋 Agent context written to: {ctx_file}")
            print(f"  ℹ️  Waiting for Claude agent execution...")
            print(f"  ℹ️  The /trust review-pr command will invoke agents automatically.")
            save_manifest(manifest, run_dir)
            return ctx_file   # Return context file; command handles the rest

        # --- Phase 4: Precision Gate ---
        _run_phase_4_precision_gate(
            manifest, run_dir, config.confidence_threshold, agents_dir
        )

        # --- Phase 5: Meta-review (MVP: basic validation) ---
        phase5 = mark_phase_start(manifest, 5, run_dir)
        gate_data = json.loads((run_dir / "gate.report.json").read_text())
        passed_findings = gate_data.get("passed", [])

        validated = []
        hallucinations = []
        diff_content = (run_dir / "diff.patch").read_text(encoding="utf-8")

        for f in passed_findings:
            quote = f.get("evidence_quote", "")
            if quote and quote in diff_content:
                validated.append(f)
            else:
                f["rejection_reason"] = "evidence_quote not found literally in diff"
                hallucinations.append(f)

        meta_report = {
            "findings_in": len(passed_findings),
            "validated": len(validated),
            "hallucinations_caught": len(hallucinations),
            "findings": validated,
            "hallucinations_caught_detail": hallucinations,
        }
        (run_dir / "meta-review.json").write_text(
            json.dumps(meta_report, indent=2), encoding="utf-8"
        )
        # Update gate report with only validated findings
        gate_data["passed"] = validated
        (run_dir / "gate.report.json").write_text(
            json.dumps(gate_data, indent=2), encoding="utf-8"
        )
        mark_phase_done(manifest, phase5, run_dir, artifact="meta-review.json")
        print(
            f"  ✅ Phase 5 done: {len(validated)} validated, "
            f"{len(hallucinations)} hallucinations intercepted"
        )

        # --- Phase 6: Traceability ---
        raw_config = config.raw
        traceability_cfg = raw_config.get("traceability", {})
        traceability_enabled = traceability_cfg.get("enabled", False)

        traceability_report: dict | None = None
        if traceability_enabled:
            validated_findings = _run_phase_6_traceability(
                manifest, run_dir, feature_branch, validated,
                traceability_cfg, setup_path,
            )
            # Read back the report for phase 7 header
            trace_file = run_dir / "traceability.json"
            if trace_file.exists():
                traceability_report = json.loads(trace_file.read_text(encoding="utf-8"))
            # Use annotated findings for phase 7
            gate_data["passed"] = validated_findings
            (run_dir / "gate.report.json").write_text(
                json.dumps(gate_data, indent=2), encoding="utf-8"
            )
        else:
            _run_phase_6_traceability_skip(manifest, run_dir)

        # --- Phase 7: Output ---
        output_base = os.environ.get(
            "TRUST_REVIEW_OUTPUT",
            str(Path.home() / "Documents" / "trust-reviews"),
        )
        output_path = (
            Path(output_base)
            / target_id
            / feature_branch.replace("/", "-")
            / "REVIEW.md"
        )
        review_path = _run_phase_7_output(
            manifest, run_dir, feature_branch, output_path,
            traceability_report=traceability_report,
        )

        # --- Finalise ---
        finalise_manifest(manifest, run_dir)
        cleanup_run(run_dir, config.retention_policy)

        print(f"\n{'─'*60}")
        print(f"✅ TRUST review complete — run {manifest.run_id}")
        print(f"\n   📋 REVIEW.md: {review_path}")
        print(f"{'─'*60}\n")

        return review_path

    except HaltError:
        # HaltError already printed the message and wrote the marker
        raise
