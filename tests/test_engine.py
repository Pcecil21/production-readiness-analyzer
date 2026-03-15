"""Tests for the analysis engine and individual checkers."""

import tempfile
from pathlib import Path

from analyzer.engine import AnalysisEngine, CHECKER_MAP
from analyzer.config import DEFAULT_CONFIG
from analyzer.models import Severity


ALL_CATEGORIES = list(CHECKER_MAP.keys())


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


def test_all_categories_run():
    """Ensure every registered category can execute without errors."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "main.py").write_text("print('hello')")
        (target / "README.md").write_text("# Test")
        engine = AnalysisEngine(target, DEFAULT_CONFIG, ALL_CATEGORIES)
        result = engine.run()
        assert len(result.categories) == len(ALL_CATEGORIES)
        for cat_name in ALL_CATEGORIES:
            assert cat_name in result.categories
            assert 0 <= result.categories[cat_name].score <= 100


def test_code_quality_detects_long_files():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "big.py").write_text("\n".join(f"x = {i}" for i in range(600)))
        engine = AnalysisEngine(target, DEFAULT_CONFIG, ["code_quality"])
        result = engine.run()
        cq = result.categories["code_quality"]
        assert any(f.check_id == "CQ-001" for f in cq.findings)


def test_code_quality_detects_sql_injection():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "db.py").write_text('cursor.execute("SELECT * FROM users WHERE id=" + user_id)')
        engine = AnalysisEngine(target, DEFAULT_CONFIG, ["code_quality"])
        result = engine.run()
        cq = result.categories["code_quality"]
        assert any(f.check_id == "CQ-004" for f in cq.findings)


def test_release_detects_version():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "package.json").write_text('{"name": "test", "version": "1.0.0"}')
        engine = AnalysisEngine(target, DEFAULT_CONFIG, ["release"])
        result = engine.run()
        rel = result.categories["release"]
        assert all(f.check_id != "SHP-001" for f in rel.findings)


def test_accessibility_skips_non_frontend():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "main.py").write_text("print('backend only')")
        engine = AnalysisEngine(target, DEFAULT_CONFIG, ["accessibility"])
        result = engine.run()
        a11y = result.categories["accessibility"]
        assert a11y.score == 100


def test_api_design_skips_non_api():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "main.py").write_text("print('no api here')")
        engine = AnalysisEngine(target, DEFAULT_CONFIG, ["api_design"])
        result = engine.run()
        api = result.categories["api_design"]
        assert api.score == 100


def test_process_detects_missing_ci():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "main.py").write_text("print('hello')")
        engine = AnalysisEngine(target, DEFAULT_CONFIG, ["process"])
        result = engine.run()
        proc = result.categories["process"]
        assert any(f.check_id == "PRC-003" for f in proc.findings)


def test_developer_experience_detects_missing_linter():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "main.py").write_text("print('hello')")
        engine = AnalysisEngine(target, DEFAULT_CONFIG, ["developer_experience"])
        result = engine.run()
        dx = result.categories["developer_experience"]
        assert any(f.check_id == "DX-001" for f in dx.findings)


def test_architecture_detects_no_config_management():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        (target / "main.py").write_text("print('hello')")
        engine = AnalysisEngine(target, DEFAULT_CONFIG, ["architecture"])
        result = engine.run()
        arc = result.categories["architecture"]
        assert any(f.check_id == "ARC-004" for f in arc.findings)


def test_json_output():
    """Ensure JSON serialization works for all categories."""
    with tempfile.TemporaryDirectory() as tmp:
        import json
        target = Path(tmp)
        (target / "main.py").write_text("print('hello')")
        engine = AnalysisEngine(target, DEFAULT_CONFIG, ALL_CATEGORIES)
        result = engine.run()
        data = json.loads(json.dumps(result.to_dict()))
        assert "overall_score" in data
        assert len(data["categories"]) == len(ALL_CATEGORIES)
