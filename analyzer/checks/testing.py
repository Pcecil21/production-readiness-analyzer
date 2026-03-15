"""Testing checks: test files, CI config, coverage, e2e tests."""

from analyzer.checks import BaseChecker
from analyzer.models import CategoryResult, Finding, Severity


class TestingChecker(BaseChecker):
    def run(self) -> CategoryResult:
        findings: list[Finding] = []
        score = 100

        # TST-001: Test files exist
        test_files = [
            f for f in self.files
            if "test" in f.name.lower() or "spec" in f.name.lower()
            or any(p.name in ("tests", "test", "__tests__", "spec") for p in f.parents)
        ]
        if not test_files:
            findings.append(Finding(
                check_id="TST-001",
                category="testing",
                severity=Severity.CRITICAL,
                message="No test files found",
            ))
            score -= 30
        elif len(test_files) < 3:
            findings.append(Finding(
                check_id="TST-001",
                category="testing",
                severity=Severity.WARNING,
                message=f"Only {len(test_files)} test file(s) found — coverage likely insufficient",
            ))
            score -= 10

        # TST-002: CI pipeline config
        ci_files = [
            f for f in self.files
            if f.name in (
                "Jenkinsfile", "Makefile", ".travis.yml", "azure-pipelines.yml",
                "bitbucket-pipelines.yml", "cloudbuild.yaml",
            )
            or ".github/workflows" in str(f).replace("\\", "/")
            or ".gitlab-ci" in f.name
            or ".circleci" in str(f).replace("\\", "/")
        ]
        if not ci_files:
            findings.append(Finding(
                check_id="TST-002",
                category="testing",
                severity=Severity.WARNING,
                message="No CI/CD pipeline configuration detected",
            ))
            score -= 20

        # TST-003: Coverage configuration
        coverage_indicators = [
            "coverageThreshold", "coverage", ".coveragerc", "codecov.yml",
            "jest.config", "pytest.ini", "setup.cfg", ".nycrc", "c8",
        ]
        has_coverage = any(
            any(ind in f.name for ind in coverage_indicators)
            for f in self.files
        )
        if not has_coverage:
            for f in self.files:
                if f.name in ("pyproject.toml", "package.json"):
                    content = self._read_safe(f)
                    if "coverage" in content.lower():
                        has_coverage = True
                        break
        if not has_coverage:
            findings.append(Finding(
                check_id="TST-003",
                category="testing",
                severity=Severity.INFO,
                message="No test coverage configuration found",
            ))
            score -= 5

        # TST-004: E2E / integration tests
        e2e_indicators = ["e2e", "integration", "playwright", "cypress", "selenium", "puppeteer"]
        has_e2e = any(
            any(ind in f.name.lower() or ind in str(f).lower() for ind in e2e_indicators)
            for f in self.files
        )
        if not has_e2e:
            findings.append(Finding(
                check_id="TST-004",
                category="testing",
                severity=Severity.INFO,
                message="No end-to-end or integration test setup detected",
            ))
            score -= 5

        return CategoryResult(name="testing", score=max(0, score), findings=findings)
