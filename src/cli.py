#!/usr/bin/env python3
"""Production Readiness Analyzer — CLI entry point.

Usage:
    python -m src.cli /path/to/your/project
    python -m src.cli /path/to/your/project --context context.json
    python -m src.cli /path/to/your/project --quick
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from .ingestion import build_manifest, save_manifest
from .context_gatherer import gather_context_interactive, gather_context_from_file, save_context
from .aggregator import aggregate_findings, save_aggregated
from .roadmap import generate_roadmap, save_roadmap
from .analyzers import ALL_ANALYZERS


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a codebase for production readiness.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.cli ../my-app                    # Interactive mode
  python -m src.cli ../my-app --context ctx.json  # Reuse saved context
  python -m src.cli ../my-app --quick             # Skip context, use defaults
  python -m src.cli ../my-app --output ./report   # Custom output dir
        """,
    )
    parser.add_argument("target", help="Path to the project directory to analyze")
    parser.add_argument("--context", "-c", help="Path to a context.json file (skip interactive questions)")
    parser.add_argument("--output", "-o", help="Output directory (default: .production-ready/ inside target)")
    parser.add_argument("--quick", "-q", action="store_true", help="Quick mode: skip context gathering, use defaults")
    parser.add_argument("--analyzers", "-a", nargs="+", help="Run only specific analyzers (e.g., security infrastructure)")
    parser.add_argument("--manifest-only", action="store_true", help="Only generate the codebase manifest")

    args = parser.parse_args()
    target = os.path.abspath(args.target)

    if not os.path.isdir(target):
        print(f"Error: '{target}' is not a directory.")
        sys.exit(1)

    output_dir = args.output or os.path.join(target, ".production-ready")
    findings_dir = os.path.join(output_dir, "findings")

    print("\n" + "=" * 60)
    print("  PRODUCTION READINESS ANALYZER")
    print("=" * 60)
    print(f"\n  Target: {target}")
    print(f"  Output: {output_dir}\n")

    # Step 1: Ingest codebase
    print("[1/5] Scanning codebase...")
    start = time.time()
    manifest = build_manifest(target)
    manifest_path = save_manifest(manifest, output_dir)
    elapsed = time.time() - start
    print(f"      Found {manifest['file_count']} files, "
          f"{', '.join(manifest['frameworks']) or 'no framework detected'}, "
          f"{manifest['dependencies']['total_count']} dependencies")
    print(f"      Manifest saved to {manifest_path} ({elapsed:.1f}s)")

    if args.manifest_only:
        print("\n  --manifest-only: stopping here.")
        print(f"  View manifest: {manifest_path}")
        return

    # Step 2: Gather context
    print("\n[2/5] Gathering context...")
    if args.context:
        context = gather_context_from_file(args.context)
        print(f"      Loaded context from {args.context}")
    elif args.quick:
        context = {
            "app_description": f"{', '.join(manifest['frameworks'])} project",
            "target_user": "unknown",
            "distribution_target": "web",
            "monetization": "not-decided",
            "timeline": "months",
            "biggest_worry": "unknown",
            "compliance_requirements": [],
        }
        print("      Using default context (quick mode)")
    else:
        context = gather_context_interactive(manifest)

    context_path = save_context(context, output_dir)
    print(f"      Context saved to {context_path}")

    # Step 3: Run analyzers
    print("\n[3/5] Running analyzers...")
    os.makedirs(findings_dir, exist_ok=True)

    analyzers_to_run = ALL_ANALYZERS
    if args.analyzers:
        names = [a.lower() for a in args.analyzers]
        analyzers_to_run = [a for a in ALL_ANALYZERS if a.name in names]
        if not analyzers_to_run:
            print(f"  Error: no matching analyzers for {args.analyzers}")
            print(f"  Available: {', '.join(a.name for a in ALL_ANALYZERS)}")
            sys.exit(1)

    total_findings = 0
    for analyzer_cls in analyzers_to_run:
        analyzer = analyzer_cls(target, manifest, context)
        start = time.time()
        findings = analyzer.run()
        path = analyzer.save(findings_dir)
        elapsed = time.time() - start
        total_findings += len(findings)

        severity_counts = {}
        for f in findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
        summary = ", ".join(f"{v} {k}" for k, v in sorted(severity_counts.items(),
                           key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(x[0], 5)))

        print(f"      {analyzer.name}: {len(findings)} findings ({summary or 'clean'}) [{elapsed:.1f}s]")

    # Step 4: Aggregate
    print(f"\n[4/5] Aggregating {total_findings} findings...")
    aggregated = aggregate_findings(findings_dir, context)
    score_path = save_aggregated(aggregated, output_dir)
    score = aggregated["score"]
    print(f"      Overall score: {score['overall']}/100 (Grade: {score['grade']})")
    print(f"      Score saved to {score_path}")

    # Step 5: Generate roadmap
    print("\n[5/5] Generating roadmap...")
    roadmap_text = generate_roadmap(aggregated, context, manifest)
    roadmap_path = save_roadmap(roadmap_text, output_dir)
    print(f"      Roadmap saved to {roadmap_path}")

    # Final summary
    print("\n" + "=" * 60)
    print(f"  DONE — Score: {score['overall']}/100 ({score['grade']})")
    print("=" * 60)
    by_sev = aggregated.get("by_severity", {})
    print(f"  {by_sev.get('critical', 0)} critical | "
          f"{by_sev.get('high', 0)} high | "
          f"{by_sev.get('medium', 0)} medium | "
          f"{by_sev.get('low', 0)} low | "
          f"{by_sev.get('info', 0)} info")
    print(f"  Estimated total effort: {aggregated.get('total_effort_hours', 0):.0f} hours")
    print(f"\n  Full report: {roadmap_path}")
    print(f"  Score details: {score_path}")
    print()


if __name__ == "__main__":
    main()
