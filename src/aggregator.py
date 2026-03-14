"""Findings aggregator — merge, deduplicate, calibrate severity, compute scores."""

from __future__ import annotations
import json
import os
from collections import Counter


SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def aggregate_findings(findings_dir: str, context: dict) -> dict:
    """Load all analyzer findings, merge, deduplicate, and compute scores."""
    all_findings = []
    analyzer_summaries = {}

    # Load all finding files
    if not os.path.isdir(findings_dir):
        return {"findings": [], "score": 0, "summary": {}}

    for fname in os.listdir(findings_dir):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(findings_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        analyzer_name = data.get("analyzer", fname.replace(".json", ""))
        findings = data.get("findings", [])
        analyzer_summaries[analyzer_name] = {
            "description": data.get("description", ""),
            "finding_count": len(findings),
            "critical": sum(1 for f in findings if f["severity"] == "critical"),
            "high": sum(1 for f in findings if f["severity"] == "high"),
            "medium": sum(1 for f in findings if f["severity"] == "medium"),
            "low": sum(1 for f in findings if f["severity"] == "low"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
        }
        all_findings.extend(findings)

    # Deduplicate by file+category (keep highest severity)
    deduped = _deduplicate(all_findings)

    # Calibrate severity based on context
    calibrated = _calibrate_severity(deduped, context)

    # Sort by severity then effort efficiency
    calibrated.sort(key=lambda f: (
        -SEVERITY_ORDER.get(f["severity"], 0),
        f.get("effort_hours", 999),
    ))

    # Compute overall score
    score = _compute_score(calibrated)

    return {
        "findings": calibrated,
        "score": score,
        "analyzer_summaries": analyzer_summaries,
        "total_findings": len(calibrated),
        "by_severity": dict(Counter(f["severity"] for f in calibrated)),
        "total_effort_hours": sum(f.get("effort_hours", 0) for f in calibrated),
    }


def _deduplicate(findings: list[dict]) -> list[dict]:
    """Remove duplicate findings (same file + same category), keeping highest severity."""
    seen = {}
    for f in findings:
        key = (f.get("file", ""), f.get("category", ""), f.get("title", "")[:50])
        existing = seen.get(key)
        if existing is None:
            seen[key] = f
        else:
            # Keep the one with higher severity
            if SEVERITY_ORDER.get(f["severity"], 0) > SEVERITY_ORDER.get(existing["severity"], 0):
                seen[key] = f
    return list(seen.values())


def _calibrate_severity(findings: list[dict], context: dict) -> list[dict]:
    """Adjust severity based on distribution target and timeline."""
    distribution = context.get("distribution_target", "web")
    timeline = context.get("timeline", "months")

    for f in findings:
        cat = f.get("category", "")

        # App Store submissions have hard requirements
        if distribution == "app-store" and cat in ("app_store", "privacy"):
            if f["severity"] == "medium":
                f["severity"] = "high"

        # Internal tools can relax some requirements
        if distribution == "internal":
            if cat in ("web_seo", "legal", "api_docs", "monetization"):
                if f["severity"] in ("high", "critical"):
                    f["severity"] = "low"

        # Short timelines: de-prioritize polish items
        if timeline == "weeks":
            if cat in ("code_cleanup", "dependencies", "test_quality", "organization"):
                if f["severity"] == "medium":
                    f["severity"] = "low"

        # API products need docs more urgently
        if distribution == "api" and cat == "api_docs":
            if f["severity"] == "medium":
                f["severity"] = "high"

    return findings


def _compute_score(findings: list[dict]) -> dict:
    """Compute a 0-100 readiness score with breakdown."""
    # Start at 100, deduct based on findings
    deductions = {"critical": 20, "high": 10, "medium": 4, "low": 1, "info": 0}
    total_deduction = 0
    category_scores = {}

    # Group findings by analyzer category
    categories = {
        "security": [],
        "infrastructure": [],
        "code_quality": [],
        "testing": [],
        "platform": [],
    }

    for f in findings:
        fid = f.get("id", "")
        if fid.startswith("SEC"):
            categories["security"].append(f)
        elif fid.startswith("INFRA"):
            categories["infrastructure"].append(f)
        elif fid.startswith("CQ"):
            categories["code_quality"].append(f)
        elif fid.startswith("TEST"):
            categories["testing"].append(f)
        elif fid.startswith("PLAT"):
            categories["platform"].append(f)

    for cat_name, cat_findings in categories.items():
        cat_deduction = sum(deductions.get(f["severity"], 0) for f in cat_findings)
        cat_score = max(0, 100 - cat_deduction)
        category_scores[cat_name] = cat_score
        total_deduction += cat_deduction

    overall = max(0, 100 - total_deduction)

    return {
        "overall": overall,
        "categories": category_scores,
        "grade": _grade(overall),
    }


def _grade(score: int) -> str:
    if score >= 80:
        return "A"
    elif score >= 60:
        return "B"
    elif score >= 40:
        return "C"
    elif score >= 20:
        return "D"
    else:
        return "F"


def save_aggregated(aggregated: dict, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "score.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(aggregated, f, indent=2)
    return path
