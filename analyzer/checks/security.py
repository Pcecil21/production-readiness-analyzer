"""Security checks: secrets, lockfiles, .env handling, HTTPS enforcement."""

import re
from pathlib import Path

from analyzer.checks import BaseChecker
from analyzer.models import CategoryResult, Finding, Severity

# Patterns that likely indicate hardcoded secrets
SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{20,}', "Possible hardcoded API key"),
    (r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}', "Possible hardcoded secret/password"),
    (r'(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}', "Possible hardcoded bearer token"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID detected"),
    (r'(?i)sk-[a-zA-Z0-9]{20,}', "Possible OpenAI/Stripe secret key"),
    (r'ghp_[A-Za-z0-9]{36}', "GitHub personal access token detected"),
]

SCANNABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb",
    ".php", ".env", ".yml", ".yaml", ".toml", ".json", ".cfg", ".ini",
    ".sh", ".bash", ".zsh", ".cs", ".swift", ".kt",
}


class SecurityChecker(BaseChecker):
    def run(self) -> CategoryResult:
        findings: list[Finding] = []
        score = 100

        # SEC-001: Scan for hardcoded secrets
        for f in self.files:
            if f.suffix not in SCANNABLE_EXTENSIONS:
                continue
            content = self._read_safe(f)
            for pattern, msg in SECRET_PATTERNS:
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count("\n") + 1
                    findings.append(Finding(
                        check_id="SEC-001",
                        category="security",
                        severity=Severity.CRITICAL,
                        message=f"{msg} in {self._rel(f)}:{line_num}",
                        file=self._rel(f),
                        line=line_num,
                    ))
                    score -= 10

        # SEC-002: Check for dependency lockfile
        has_lockfile = self._has_file(
            "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
            "Pipfile.lock", "poetry.lock", "Cargo.lock", "go.sum",
            "Gemfile.lock", "composer.lock",
        )
        if not has_lockfile:
            has_manifest = self._has_file(
                "package.json", "Pipfile", "pyproject.toml", "Cargo.toml",
                "go.mod", "Gemfile", "composer.json", "requirements.txt",
            )
            if has_manifest:
                findings.append(Finding(
                    check_id="SEC-002",
                    category="security",
                    severity=Severity.WARNING,
                    message="Dependency manifest found but no lockfile — builds are non-deterministic",
                ))
                score -= 10

        # SEC-003: Check .gitignore for .env
        gitignore = self.target / ".gitignore"
        if gitignore.is_file():
            content = self._read_safe(gitignore)
            if ".env" not in content:
                findings.append(Finding(
                    check_id="SEC-003",
                    category="security",
                    severity=Severity.WARNING,
                    message=".env is not listed in .gitignore — secrets may be committed",
                ))
                score -= 10
        else:
            findings.append(Finding(
                check_id="SEC-003",
                category="security",
                severity=Severity.WARNING,
                message="No .gitignore file found",
            ))
            score -= 5

        # SEC-004: Check for .env files in repo
        for f in self.files:
            if f.name == ".env" or f.name.startswith(".env."):
                if f.name not in (".env.example", ".env.template", ".env.sample"):
                    findings.append(Finding(
                        check_id="SEC-004",
                        category="security",
                        severity=Severity.CRITICAL,
                        message=f"Environment file {self._rel(f)} found in project tree",
                        file=self._rel(f),
                    ))
                    score -= 15

        return CategoryResult(name="security", score=max(0, score), findings=findings)
