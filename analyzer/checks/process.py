"""Engineering process checks — inspired by retro, qa, loop skills.

Evaluates CI/CD maturity, PR templates, issue templates, monitoring,
scheduled tasks, and quality gates.
"""

import re

from analyzer.checks import BaseChecker
from analyzer.models import CategoryResult, Finding, Severity


class ProcessChecker(BaseChecker):
    def run(self) -> CategoryResult:
        findings: list[Finding] = []
        score = 100

        file_names = {f.name for f in self.files}
        rel_paths = [self._rel(f) for f in self.files]

        # PRC-001: PR template
        has_pr_template = any(
            "pull_request_template" in p.lower() or "pr_template" in p.lower()
            for p in rel_paths
        )
        if not has_pr_template:
            findings.append(Finding(
                check_id="PRC-001",
                category="process",
                severity=Severity.INFO,
                message="No pull request template — PRs will lack consistent structure and review checklists",
            ))
            score -= 5

        # PRC-002: Issue templates
        has_issue_template = any(
            "issue_template" in p.lower() or "bug_report" in p.lower() or "feature_request" in p.lower()
            for p in rel_paths
        )
        if not has_issue_template:
            findings.append(Finding(
                check_id="PRC-002",
                category="process",
                severity=Severity.INFO,
                message="No issue templates — bug reports and feature requests will lack structure",
            ))
            score -= 3

        # PRC-003: CI pipeline completeness
        ci_files = [
            f for f in self.files
            if ".github/workflows" in str(f).replace("\\", "/")
            or ".gitlab-ci" in f.name
            or ".circleci" in str(f).replace("\\", "/")
            or f.name in ("Jenkinsfile", ".travis.yml", "azure-pipelines.yml")
        ]
        if ci_files:
            ci_content = "\n".join(self._read_safe(f) for f in ci_files)

            # Check for test step
            has_test_step = re.search(r'(test|spec|pytest|jest|mocha|rspec|go test|cargo test)', ci_content, re.IGNORECASE)
            if not has_test_step:
                findings.append(Finding(
                    check_id="PRC-003",
                    category="process",
                    severity=Severity.WARNING,
                    message="CI pipeline exists but no test step detected — tests aren't gatekeeping merges",
                ))
                score -= 15

            # Check for lint step
            has_lint_step = re.search(r'(lint|eslint|flake8|ruff|rubocop|golangci|clippy|biome)', ci_content, re.IGNORECASE)
            if not has_lint_step:
                findings.append(Finding(
                    check_id="PRC-004",
                    category="process",
                    severity=Severity.INFO,
                    message="CI pipeline has no linting step — style issues will reach main branch",
                ))
                score -= 5

            # Check for security scanning
            has_security_scan = re.search(
                r'(snyk|dependabot|renovate|trivy|codeql|semgrep|bandit|safety|audit)',
                ci_content, re.IGNORECASE,
            )
            if not has_security_scan:
                findings.append(Finding(
                    check_id="PRC-005",
                    category="process",
                    severity=Severity.WARNING,
                    message="CI has no security/dependency scanning — vulnerabilities won't be caught automatically",
                ))
                score -= 10

            # Check for build/deploy step
            has_deploy = re.search(r'(deploy|publish|release|push.*registry|docker.*push)', ci_content, re.IGNORECASE)
            if not has_deploy:
                findings.append(Finding(
                    check_id="PRC-006",
                    category="process",
                    severity=Severity.INFO,
                    message="CI has no deploy/publish step — releases require manual intervention",
                ))
                score -= 5
        else:
            findings.append(Finding(
                check_id="PRC-003",
                category="process",
                severity=Severity.CRITICAL,
                message="No CI/CD pipeline — code changes have no automated quality gate",
            ))
            score -= 25

        # PRC-007: Dependabot / Renovate for dependency updates
        dep_update_files = [
            f for f in self.files
            if "dependabot" in f.name.lower() or "renovate" in f.name.lower()
        ]
        if not dep_update_files:
            findings.append(Finding(
                check_id="PRC-007",
                category="process",
                severity=Severity.INFO,
                message="No Dependabot/Renovate config — dependency updates won't be automated",
            ))
            score -= 5

        # PRC-008: Monitoring and scheduled checks (cron-like)
        all_content = "\n".join(self._read_safe(f) for f in ci_files) if ci_files else ""
        has_cron = re.search(r'(cron|schedule|recurring|periodic)', all_content, re.IGNORECASE)
        if not has_cron:
            findings.append(Finding(
                check_id="PRC-008",
                category="process",
                severity=Severity.INFO,
                message="No scheduled CI jobs — consider nightly builds, dependency checks, or health monitoring",
            ))
            score -= 3

        # PRC-009: Code review enforcement (CODEOWNERS)
        has_codeowners = "CODEOWNERS" in file_names
        if not has_codeowners:
            findings.append(Finding(
                check_id="PRC-009",
                category="process",
                severity=Severity.INFO,
                message="No CODEOWNERS file — code review assignments aren't automated",
            ))
            score -= 3

        return CategoryResult(name="process", score=max(0, score), findings=findings)
