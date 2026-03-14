"""Roadmap generator — phased, prioritized markdown output."""

from __future__ import annotations
import os
from datetime import datetime


PHASE_DEFINITIONS = {
    "phase_0": {
        "name": "Phase 0: Stop the Bleeding",
        "desc": "Issues that are actively dangerous or will block all other work.",
        "severities": ["critical"],
    },
    "phase_1": {
        "name": "Phase 1: Foundation",
        "desc": "Must-fix for any production use. Issues that any user or reviewer would hit.",
        "severities": ["high"],
    },
    "phase_2": {
        "name": "Phase 2: Production Infrastructure",
        "desc": "Monitoring, CI/CD, error tracking — things that let you operate the app once it's live.",
        "severities": ["medium"],
        "categories": ["monitoring", "ci_cd", "logging", "error_handling", "health_check",
                       "backup", "deployment", "env_management", "database"],
    },
    "phase_3": {
        "name": "Phase 3: Quality & Polish",
        "desc": "Testing, performance, code cleanup — things that determine whether users stay.",
        "severities": ["medium"],
        "categories": ["test_existence", "test_coverage", "test_framework", "test_types",
                       "file_size", "type_safety", "error_handling", "code_debt",
                       "organization", "code_cleanup", "dependencies",
                       "web_seo", "web_ux", "documentation"],
    },
    "phase_4": {
        "name": "Phase 4: Growth Readiness",
        "desc": "Scalability, analytics, compliance — things you need when trying to grow.",
        "severities": ["low"],
    },
}


def generate_roadmap(aggregated: dict, context: dict, manifest: dict) -> str:
    """Generate a phased markdown roadmap from aggregated findings."""
    findings = aggregated["findings"]
    score = aggregated["score"]

    lines = []
    lines.append("# Production Readiness Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Target:** {manifest.get('target_dir', 'unknown')}")
    lines.append(f"**Stack:** {', '.join(manifest.get('frameworks', ['unknown']))}")
    lines.append(f"**Distribution:** {context.get('distribution_target', 'unknown')}")
    lines.append(f"**Monetization:** {context.get('monetization', 'unknown')}")
    lines.append(f"**Timeline:** {context.get('timeline', 'unknown')}")
    lines.append("")

    # Score dashboard
    lines.append("---")
    lines.append("")
    lines.append("## Readiness Score")
    lines.append("")
    overall = score.get("overall", 0)
    grade = score.get("grade", "?")
    lines.append(f"### Overall: {overall}/100 (Grade: {grade})")
    lines.append("")

    cat_scores = score.get("categories", {})
    lines.append("| Category | Score |")
    lines.append("|----------|-------|")
    for cat, s in cat_scores.items():
        label = cat.replace("_", " ").title()
        bar = _score_bar(s)
        lines.append(f"| {label} | {s}/100 {bar} |")
    lines.append("")

    # Summary counts
    by_sev = aggregated.get("by_severity", {})
    total_effort = aggregated.get("total_effort_hours", 0)
    lines.append(f"**Total findings:** {aggregated.get('total_findings', 0)}")
    lines.append(f"**Estimated total effort:** {total_effort:.0f} hours")
    lines.append(f"**Breakdown:** {by_sev.get('critical', 0)} critical, "
                 f"{by_sev.get('high', 0)} high, "
                 f"{by_sev.get('medium', 0)} medium, "
                 f"{by_sev.get('low', 0)} low, "
                 f"{by_sev.get('info', 0)} info")
    lines.append("")

    # Phased roadmap
    lines.append("---")
    lines.append("")
    lines.append("## Phased Roadmap")

    assigned = set()

    for phase_key, phase_def in PHASE_DEFINITIONS.items():
        phase_findings = _assign_to_phase(findings, phase_def, assigned)
        if not phase_findings:
            continue

        lines.append("")
        lines.append(f"### {phase_def['name']}")
        lines.append(f"*{phase_def['desc']}*")
        lines.append("")

        phase_effort = sum(f.get("effort_hours", 0) for f in phase_findings)
        lines.append(f"**Items:** {len(phase_findings)} | **Estimated effort:** {phase_effort:.0f}h")
        lines.append("")

        for f in phase_findings:
            sev = f["severity"].upper()
            effort = f.get("effort_hours", 0)
            lines.append(f"#### [{sev}] {f['title']}")
            if f.get("file"):
                loc = f["file"]
                if f.get("line"):
                    loc += f":{f['line']}"
                lines.append(f"**Location:** `{loc}`")
            lines.append(f"**Effort:** ~{effort:.0f}h | **ID:** {f['id']}")
            lines.append("")
            if f.get("description"):
                lines.append(f"{f['description']}")
                lines.append("")
            if f.get("why_it_matters"):
                lines.append(f"**Why it matters:** {f['why_it_matters']}")
                lines.append("")
            if f.get("recommendation"):
                lines.append(f"**What to do:** {f['recommendation']}")
                lines.append("")
            if f.get("depends_on"):
                lines.append(f"**Depends on:** {', '.join(f['depends_on'])}")
                lines.append("")
            lines.append("---")
            lines.append("")

    # Parking lot — info-level findings
    info_findings = [f for f in findings if f["severity"] == "info" and f["id"] not in assigned]
    if info_findings:
        lines.append("### Parking Lot: Not Now")
        lines.append("*Issues that are real but not worth addressing given your current goals and timeline.*")
        lines.append("")
        for f in info_findings:
            lines.append(f"- **{f['title']}** ({f['id']}): {f.get('recommendation', '')}")
        lines.append("")

    # Context summary at the bottom
    lines.append("---")
    lines.append("")
    lines.append("## Analysis Context")
    lines.append("")
    lines.append(f"- **App:** {context.get('app_description', 'N/A')}")
    lines.append(f"- **Target user:** {context.get('target_user', 'N/A')}")
    lines.append(f"- **Biggest worry:** {context.get('biggest_worry', 'N/A')}")
    compliance = context.get("compliance_requirements", [])
    lines.append(f"- **Compliance:** {', '.join(compliance) if compliance else 'None specified'}")
    lines.append("")
    lines.append("---")
    lines.append("*Generated by Production Readiness Analyzer*")

    return "\n".join(lines)


def _assign_to_phase(findings: list, phase_def: dict, assigned: set) -> list:
    """Assign findings to a phase based on severity and optionally category."""
    result = []
    target_severities = phase_def.get("severities", [])
    target_categories = phase_def.get("categories")

    for f in findings:
        if f["id"] in assigned:
            continue
        if f["severity"] not in target_severities:
            continue
        if target_categories is not None and f.get("category") not in target_categories:
            continue
        result.append(f)
        assigned.add(f["id"])

    return result


def _score_bar(score: int) -> str:
    """Generate a simple text progress bar."""
    filled = score // 10
    empty = 10 - filled
    return "[" + "#" * filled + "-" * empty + "]"


def save_roadmap(roadmap_text: str, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "roadmap.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(roadmap_text)
    return path
