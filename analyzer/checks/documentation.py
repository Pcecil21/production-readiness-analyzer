"""Documentation checks: README, API docs, runbooks, ADRs, changelog."""

from analyzer.checks import BaseChecker
from analyzer.models import CategoryResult, Finding, Severity


class DocumentationChecker(BaseChecker):
    def run(self) -> CategoryResult:
        findings: list[Finding] = []
        score = 100

        # DOC-001: README exists and has substance
        readme_files = [f for f in self.files if f.name.lower().startswith("readme")]
        if not readme_files:
            findings.append(Finding(
                check_id="DOC-001",
                category="documentation",
                severity=Severity.CRITICAL,
                message="No README file found",
            ))
            score -= 25
        else:
            content = self._read_safe(readme_files[0])
            if len(content.strip()) < 200:
                findings.append(Finding(
                    check_id="DOC-001",
                    category="documentation",
                    severity=Severity.WARNING,
                    message="README exists but is very short — may lack setup/usage instructions",
                ))
                score -= 10

        # DOC-002: CHANGELOG
        has_changelog = self._has_file("CHANGELOG.md", "CHANGELOG", "CHANGES.md", "HISTORY.md")
        if not has_changelog:
            findings.append(Finding(
                check_id="DOC-002",
                category="documentation",
                severity=Severity.INFO,
                message="No CHANGELOG file found",
            ))
            score -= 5

        # DOC-003: API documentation
        api_indicators = [
            "openapi", "swagger", "api-docs", "apidoc",
            "redoc", "slate", "stoplight",
        ]
        has_api_docs = any(
            any(ind in f.name.lower() or ind in str(f).lower() for ind in api_indicators)
            for f in self.files
        )
        # Also check for inline doc generation configs
        doc_gen = self._has_file("mkdocs.yml", "sphinx", "typedoc.json", "jsdoc.json", ".readthedocs.yml")
        if not has_api_docs and not doc_gen:
            findings.append(Finding(
                check_id="DOC-003",
                category="documentation",
                severity=Severity.INFO,
                message="No API documentation or doc generation config found",
            ))
            score -= 10

        # DOC-004: Architecture Decision Records
        adr_dirs = [f for f in self.files if "adr" in str(f).lower() and f.suffix in (".md", ".txt")]
        if not adr_dirs:
            findings.append(Finding(
                check_id="DOC-004",
                category="documentation",
                severity=Severity.INFO,
                message="No Architecture Decision Records (ADRs) found — design rationale may be lost",
            ))
            score -= 5

        # DOC-005: Contributing guide
        has_contributing = self._has_file("CONTRIBUTING.md", "CONTRIBUTING", "CONTRIBUTING.txt")
        if not has_contributing:
            findings.append(Finding(
                check_id="DOC-005",
                category="documentation",
                severity=Severity.INFO,
                message="No CONTRIBUTING guide found",
            ))
            score -= 5

        return CategoryResult(name="documentation", score=max(0, score), findings=findings)
