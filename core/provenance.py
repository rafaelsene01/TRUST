"""Provenance tracking for TRUST v2.0 — Enterprise profile.

In the Enterprise profile, every finding must declare which layer's
checklist rule triggered it: corp, team, or personal.  This lets the
enterprise know whether a finding comes from a company-wide policy
(corp) or from a team convention (team), and surfaces it in REVIEW.md.

The ``provenance`` field injected into each finding dict:

    ```json
    {
      "rule_id": "SEC-003",
      ...,
      "provenance": {
        "layer": "corp",
        "rule_id": "SEC-003",
        "overridden_by": null
      }
    }
    ```

When a rule was overridden by a higher-priority layer:

    ```json
    "provenance": {
      "layer": "corp",
      "rule_id": "SEC-003",
      "overridden_by": "team",
      "override_reason": "We use HSM — control does not apply here"
    }
    ```

Note: non-enterprise profiles still produce valid REVIEW.md without
provenance — this module is only called when profile_type == enterprise.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ProvenanceEntry:
    """Provenance metadata for a single finding."""

    layer: str                    # "corp" | "team" | "personal"
    rule_id: str
    overridden_by: str | None = None
    override_reason: str | None = None

    def to_dict(self) -> dict:
        d: dict = {"layer": self.layer, "rule_id": self.rule_id}
        if self.overridden_by:
            d["overridden_by"] = self.overridden_by
        if self.override_reason:
            d["override_reason"] = self.override_reason
        return d


# ---------------------------------------------------------------------------
# Tagging helpers
# ---------------------------------------------------------------------------


def tag_finding(finding: dict, layer_name: str) -> dict:
    """Return a copy of finding with a ``provenance`` block injected."""
    copy = dict(finding)
    entry = ProvenanceEntry(
        layer=layer_name,
        rule_id=finding.get("rule_id", ""),
    )
    copy["provenance"] = entry.to_dict()
    return copy


def tag_findings(findings: list[dict], layer_name: str) -> list[dict]:
    """Tag all findings in a list with the given layer name."""
    return [tag_finding(f, layer_name) for f in findings]


def apply_override_to_finding(
    finding: dict,
    override_layer: str,
    override_reason: str,
) -> dict:
    """Mark a finding as overridden by a higher-priority layer."""
    copy = dict(finding)
    existing = copy.get("provenance", {})
    copy["provenance"] = {
        **existing,
        "overridden_by": override_layer,
        "override_reason": override_reason,
    }
    return copy


# ---------------------------------------------------------------------------
# Provenance report
# ---------------------------------------------------------------------------


def build_provenance_report(findings: list[dict]) -> dict:
    """Summarise findings by layer for the REVIEW.md appendix.

    Returns a dict with:
        by_layer: {layer_name: [rule_ids]}
        overrides_applied: [{rule_id, original_layer, overriding_layer, reason}]
        total: int
    """
    by_layer: dict[str, list[str]] = {}
    overrides_applied: list[dict] = []

    for f in findings:
        prov = f.get("provenance", {})
        layer = prov.get("layer", "unknown")
        rule_id = f.get("rule_id", "?")

        by_layer.setdefault(layer, []).append(rule_id)

        if prov.get("overridden_by"):
            overrides_applied.append({
                "rule_id": rule_id,
                "original_layer": layer,
                "overriding_layer": prov["overridden_by"],
                "reason": prov.get("override_reason", ""),
            })

    return {
        "by_layer": by_layer,
        "overrides_applied": overrides_applied,
        "total": len(findings),
    }


def format_provenance_appendix(report: dict) -> str:
    """Return a Markdown snippet for the REVIEW.md provenance appendix."""
    lines = [
        "\n<details>",
        "<summary>🏢 Provenance — findings by layer</summary>\n",
    ]

    by_layer = report.get("by_layer", {})
    layer_order = ["corp", "team", "personal"]
    for layer in layer_order + [l for l in by_layer if l not in layer_order]:
        rules = by_layer.get(layer, [])
        if not rules:
            continue
        icon = {"corp": "🏛️", "team": "👥", "personal": "👤"}.get(layer, "•")
        lines.append(f"**{icon} {layer.capitalize()} layer** ({len(rules)} findings)")
        for rule_id in sorted(set(rules)):
            lines.append(f"  - `{rule_id}`")
        lines.append("")

    overrides = report.get("overrides_applied", [])
    if overrides:
        lines.append(f"**Override log ({len(overrides)} applied):**\n")
        for o in overrides:
            reason = f" — {o['reason']}" if o.get("reason") else ""
            lines.append(
                f"  - `{o['rule_id']}`: {o['original_layer']} → "
                f"{o['overriding_layer']}{reason}"
            )

    lines.append("</details>")
    return "\n".join(lines)
