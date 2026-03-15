"""CLI entry point for production-readiness-analyzer."""

import json
import sys
from pathlib import Path

import click
from rich.console import Console

from analyzer.engine import AnalysisEngine
from analyzer.config import load_config
from analyzer.report import render_text_report, render_json_report

VALID_CATEGORIES = ["security", "reliability", "observability", "testing", "documentation", "operations"]

console = Console()


@click.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text", help="Output format.")
@click.option("--categories", default=None, help="Comma-separated list of categories to check.")
@click.option("--config", "config_path", type=click.Path(), default=None, help="Path to .readiness.yml config.")
@click.option("--threshold", type=int, default=None, help="Minimum overall score to pass (exit 0).")
def main(path: str, fmt: str, categories: str | None, config_path: str | None, threshold: int | None):
    """Analyze a codebase for production readiness."""
    target = Path(path).resolve()

    # Load config
    cfg = load_config(config_path or target / ".readiness.yml")

    # Parse categories
    if categories:
        selected = [c.strip() for c in categories.split(",")]
        invalid = [c for c in selected if c not in VALID_CATEGORIES]
        if invalid:
            console.print(f"[red]Unknown categories: {', '.join(invalid)}[/red]")
            sys.exit(2)
    else:
        selected = VALID_CATEGORIES

    # Run analysis
    engine = AnalysisEngine(target, cfg, selected)
    results = engine.run()

    # Render output
    if fmt == "json":
        click.echo(render_json_report(results))
    else:
        render_text_report(results, console)

    # Exit code based on threshold
    t = threshold or cfg.get("thresholds", {}).get("overall", 0)
    if t and results.overall_score < t:
        sys.exit(1)
