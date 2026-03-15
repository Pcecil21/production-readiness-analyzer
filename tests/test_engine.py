"""Tests for the analysis engine and individual checkers."""

import tempfile
from pathlib import Path

from analyzer.engine import AnalysisEngine
from analyzer.config import DEFAULT_CONFIG
from analyzer.models import Severity


def _make_project(tmp: Path, files: dict[str, str]) -> Path:
    """Create a temporary project with the given file structure."""
    for name, content in files.items():
        p = tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return tmp


def test_empty_project_scores_low():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "main.py").write_text("print('hello')")
        engine = AnalysisEngine(target, DEFAULT_CONFIG, ["security", "testing", "documentation"])
        result = engine.run()
        assert result.overall_score < 80


def test_secrets_detected():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "config.py").write_text('API_KEY = "AKIA1234567890ABCDEF"')
        engine = AnalysisEngine(target, DEFAULT_CONFIG, ["security"])
        result = engine.run()
        sec = result.categories["security"]
        critical_ids = [f.check_id for f in sec.findings if f.severity == Severity.CRITICAL]
        assert "SEC-001" in critical_ids


def test_good_project_scores_higher():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        files = {
            "README.md": "# My Project\n\nThis is a well-documented project with setup instructions, usage guide, and API reference.\n" + "x" * 300,
            ".gitignore": ".env\nnode_modules/\n",
            "package.json": '{"name": "test", "scripts": {"test": "jest"}}',
            "package-lock.json": "{}",
            "tests/test_main.py": "def test_something(): pass",
            "tests/test_api.py": "def test_api(): pass",
            "tests/test_utils.py": "def test_utils(): pass",
            ".github/workflows/ci.yml": "name: CI\non: push\njobs: {}",
            "src/app.py": "from structlog import get_logger\n@app.route('/health')\ndef health(): return 'ok'",
            "Dockerfile": "FROM python:3.12\nCOPY . .",
            ".dockerignore": "node_modules\n.git\n",
            "CHANGELOG.md": "# Changelog\n## 0.1.0\n- Initial release",
        }
        _make_project(target, files)
        engine = AnalysisEngine(target, DEFAULT_CONFIG, [
            "security", "testing", "documentation", "operations", "reliability", "observability",
        ])
        result = engine.run()
        assert result.overall_score > 50


def test_disabled_checks():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "config.py").write_text('API_KEY = "AKIA1234567890ABCDEF"')
        cfg = {**DEFAULT_CONFIG, "disabled_checks": ["SEC-001"]}
        engine = AnalysisEngine(target, cfg, ["security"])
        result = engine.run()
        sec = result.categories["security"]
        assert all(f.check_id != "SEC-001" for f in sec.findings)
