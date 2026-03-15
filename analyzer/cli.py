"""CLI entry point for production-readiness-analyzer."""

import json
import sys
from pathlib import Path

import click
from rich.console import Console

from analyzer.engine import AnalysisEngine, CHECKER_MAP
from analyzer.config import load_config
from analyzer.report import render_text_report, render_json_report

VALID_CATEGORIES = list(CHECKER_MAP.keys())

console = Console()


@click.command()
@click.argument("path", type=click.Path(exists=True), default=".")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text", help="Output format.")
@click.option("--categories", default=None, help="Comma-separated list of categories to check.")
@click.option("--config", "config_path", type=click.Path(), default=None, help="Path to .readiness.yml config.")
@click.option("--threshold", type=int, default=None, help="Minimum overall score to pass (exit 0).")
@click.option("--list-categories", is_flag=True, help="List all available check categories and exit.")
def main(path: str, fmt: str, categories: str | None, config_path: str | None, threshold: int | None, list_categories: bool):
    """Analyze a codebase for production readiness."""
    if list_categories:
        console.print("[bold]Available categories:[/bold]")
        for cat in VALID_CATEGORIES:
            console.print(f"  {cat}")
        return

    target = Path(path).resolve()

    # Load config
    cfg = load_config(config_path or target / ".readiness.yml")

    # Parse categories
    if categories:
        selected = [c.strip() for c in categories.split(",")]
        invalid = [c for c in selected if c not in VALID_CATEGORIES]
        if invalid:
            console.print(f"[red]Unknown categories: {', '.join(invalid)}[/red]")
            console.print(f"[dim]Valid: {', '.join(VALID_CATEGORIES)}[/dim]")
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
