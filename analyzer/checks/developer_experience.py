"""Developer experience checks — inspired by keybindings-help, setup-browser-cookies skills.

Evaluates onboarding friction, development tooling, linting/formatting config,
editor settings, and contribution guidelines.
"""

import re

from analyzer.checks import BaseChecker
from analyzer.models import CategoryResult, Finding, Severity


class DeveloperExperienceChecker(BaseChecker):
    def run(self) -> CategoryResult:
        findings: list[Finding] = []
        score = 100

        file_names = {f.name for f in self.files}
        file_names_lower = {f.name.lower() for f in self.files}

        # DX-001: Linting configuration
        lint_configs = [
            ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml", "eslint.config.js", "eslint.config.mjs",
            ".pylintrc", "pyproject.toml", "setup.cfg", ".flake8", "ruff.toml", ".ruff.toml",
            ".rubocop.yml", ".golangci.yml", ".golangci.yaml",
            "biome.json", "biome.jsonc",
        ]
        has_linter = any(f in file_names for f in lint_configs)
        # Also check pyproject.toml for ruff/flake8/pylint config
        if not has_linter:
            for f in self.files:
                if f.name == "pyproject.toml":
                    content = self._read_safe(f)
                    if any(tool in content for tool in ["[tool.ruff", "[tool.pylint", "[tool.flake8"]):
                        has_linter = True
                        break
        if not has_linter:
            findings.append(Finding(
                check_id="DX-001",
                category="developer_experience",
                severity=Severity.WARNING,
                message="No linting configuration found — code style will drift between contributors",
            ))
            score -= 10

        # DX-002: Code formatter
        formatter_configs = [
            ".prettierrc", ".prettierrc.js", ".prettierrc.json", "prettier.config.js",
            ".editorconfig", ".clang-format", "rustfmt.toml", ".scalafmt.conf",
            "biome.json",
        ]
        has_formatter = any(f in file_names for f in formatter_configs)
        if not has_formatter:
            # Check pyproject for black/ruff format
            for f in self.files:
                if f.name == "pyproject.toml":
                    content = self._read_safe(f)
                    if any(t in content for t in ["[tool.black", "[tool.ruff", "ruff format"]):
                        has_formatter = True
                        break
        if not has_formatter:
            findings.append(Finding(
                check_id="DX-002",
                category="developer_experience",
                severity=Severity.INFO,
                message="No code formatter configured — formatting debates will waste review time",
            ))
            score -= 5

        # DX-003: Pre-commit hooks
        has_hooks = any(f in file_names for f in [".pre-commit-config.yaml", ".husky", "lefthook.yml", "lint-staged.config.js"])
        husky_dir = any("husky" in str(f).lower() for f in self.files)
        if not has_hooks and not husky_dir:
            findings.append(Finding(
                check_id="DX-003",
                category="developer_experience",
                severity=Severity.INFO,
                message="No pre-commit hooks configured — linting/formatting won't be enforced locally",
            ))
            score -= 5

        # DX-004: Editor / IDE settings
        editor_configs = [".editorconfig", ".vscode", ".idea", "workspace.code-workspace"]
        has_editor = any(
            any(ec in str(f).replace("\\", "/") for ec in editor_configs)
            for f in self.files
        )
        if not has_editor:
            findings.append(Finding(
                check_id="DX-004",
                category="developer_experience",
                severity=Severity.INFO,
                message="No .editorconfig or IDE settings — contributors will have inconsistent editor behavior",
            ))
            score -= 3

        # DX-005: Makefile / task runner
        task_runners = [
            "Makefile", "Taskfile.yml", "Justfile", "Rakefile",
            "Gruntfile.js", "gulpfile.js", "nx.json", "turbo.json",
        ]
        has_tasks = any(f in file_names for f in task_runners)
        # Also check package.json scripts
        if not has_tasks:
            for f in self.files:
                if f.name == "package.json":
                    content = self._read_safe(f)
                    if '"scripts"' in content:
                        has_tasks = True
                        break
        if not has_tasks:
            findings.append(Finding(
                check_id="DX-005",
                category="developer_experience",
                severity=Severity.WARNING,
                message="No task runner (Makefile, Taskfile, npm scripts) — common tasks aren't discoverable or standardized",
            ))
            score -= 10

        # DX-006: Contributing guide
        has_contributing = "contributing.md" in file_names_lower or "contributing" in file_names_lower
        if not has_contributing:
            findings.append(Finding(
                check_id="DX-006",
                category="developer_experience",
                severity=Severity.INFO,
                message="No CONTRIBUTING guide — new developers won't know the workflow",
            ))
            score -= 5

        # DX-007: Dev container / devcontainer.json
        has_devcontainer = any("devcontainer" in str(f).lower() for f in self.files)
        if not has_devcontainer:
            findings.append(Finding(
                check_id="DX-007",
                category="developer_experience",
                severity=Severity.INFO,
                message="No dev container configuration — environment setup isn't reproducible",
            ))
            score -= 3

        # DX-008: README has setup/install instructions
        readme_files = [f for f in self.files if f.name.lower().startswith("readme")]
        if readme_files:
            content = self._read_safe(readme_files[0])
            setup_keywords = ["install", "setup", "getting started", "quick start", "prerequisites"]
            has_setup = any(kw in content.lower() for kw in setup_keywords)
            if not has_setup:
                findings.append(Finding(
                    check_id="DX-008",
                    category="developer_experience",
                    severity=Severity.WARNING,
                    message="README exists but lacks setup/install instructions",
                ))
                score -= 10

        return CategoryResult(name="developer_experience", score=max(0, score), findings=findings)
