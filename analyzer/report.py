"""Report rendering for text and JSON output."""

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from analyzer.models import AnalysisResult, Severity


def _score_color(score: int) -> str:
    if score >= 80:
        return "green"
    if score >= 60:
        return "yellow"
    return "red"


def _score_label(score: int) -> str:
    if score >= 90:
        return "EXCELLENT"
    if score >= 80:
        return "GOOD"
    if score >= 60:
        return "NEEDS WORK"
    if score >= 40:
        return "POOR"
    return "CRITICAL"


def _bar(score: int, width: int = 20) -> str:
    filled = round(score / 100 * width)
    return "\u2588" * filled + "\u2591" * (width - filled)


def render_text_report(result: AnalysisResult, console: Console) -> None:
    """Render a human-readable report to the console."""
    color = _score_color(result.overall_score)
    label = _score_label(result.overall_score)

    console.print()
    console.print(Panel(
        f"[bold]Overall Score: {result.overall_score}/100[/bold]  "
        f"[{color}]{_bar(result.overall_score)}[/{color}]  "
        f"[bold {color}]{label}[/bold {color}]",
        title=f"[bold]Production Readiness Report: {result.project_name}[/bold]",
        width=72,
    ))
    console.print()

    # Category breakdown
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Category", min_width=18)
    table.add_column("Score", min_width=10)
    table.add_column("Bar", min_width=22)

    for cat in result.categories.values():
        c = _score_color(cat.score)
        table.add_row(
            cat.name.capitalize(),
            f"[{c}]{cat.score}/100[/{c}]",
            f"[{c}]{_bar(cat.score)}[/{c}]",
        )

    console.print(table)
    console.print()

    # Critical findings
    criticals = result.critical_findings
    if criticals:
        console.print(f"[bold red]Critical Issues ({len(criticals)}):[/bold red]")
        for f in criticals:
            loc = ""
            if f.file:
                loc = f" in {f.file}"
                if f.line:
                    loc += f":{f.line}"
            console.print(f"  [red][{f.check_id}][/red] {f.message}")
        console.print()

    # Warnings
    warnings = result.warnings
    if warnings:
        console.print(f"[bold yellow]Warnings ({len(warnings)}):[/bold yellow]")
        for f in warnings:
            console.print(f"  [yellow][{f.check_id}][/yellow] {f.message}")
        console.print()

    # Info
    infos = []
    for cat in result.categories.values():
        infos.extend(f for f in cat.findings if f.severity == Severity.INFO)
    if infos:
        console.print(f"[dim]Info ({len(infos)}):[/dim]")
        for f in infos:
            console.print(f"  [dim][{f.check_id}] {f.message}[/dim]")
        console.print()


def render_json_report(result: AnalysisResult) -> str:
    """Render a JSON report."""
    return json.dumps(result.to_dict(), indent=2)
