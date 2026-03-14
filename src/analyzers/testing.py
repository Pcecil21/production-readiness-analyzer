"""Testing posture analyzer — test presence, coverage, frameworks, test quality signals."""

from __future__ import annotations
import os
import re
from .base import BaseAnalyzer


TEST_FRAMEWORKS = {
    "jest": ["jest", "@jest/core"],
    "vitest": ["vitest"],
    "mocha": ["mocha"],
    "cypress": ["cypress"],
    "playwright": ["playwright", "@playwright/test"],
    "testing-library": ["@testing-library/react", "@testing-library/vue", "@testing-library/jest-dom"],
    "pytest": ["pytest"],
    "unittest": [],  # built-in, detected via imports
    "rspec": ["rspec"],
    "go-test": [],  # built-in
}


class TestingAnalyzer(BaseAnalyzer):
    name = "testing"
    description = "Test presence, coverage, frameworks, test quality signals"

    def run(self) -> list:
        self._check_test_existence()
        self._check_test_framework()
        self._check_test_coverage_config()
        self._check_test_types()
        self._check_test_scripts()
        self._check_test_quality()
        return self.findings

    def _check_test_existence(self):
        test_files = self.manifest.get("test_files", [])
        file_count = self.manifest.get("file_count", 0)
        distribution = self.context.get("distribution_target", "web")
        timeline = self.context.get("timeline", "months")

        if not test_files:
            # Severity depends on context
            if distribution in ("web-saas", "api") and timeline != "weeks":
                severity = "high"
            else:
                severity = "medium"

            self._add(
                id=self._next_id("TEST"),
                severity=severity,
                category="test_existence",
                title="No test files found",
                description="Zero test files detected in the project.",
                why_it_matters="Without tests, every change risks breaking existing functionality. Refactoring becomes terrifying. Bug fixes introduce new bugs.",
                recommendation="Start with the highest-value tests: API route tests (catch regressions in your core logic) and critical user flow tests (signup, payment, core feature). Don't aim for 100% coverage — aim for confidence in your critical paths.",
                effort_hours=16,
            )
        else:
            # Check test-to-source ratio
            code_exts = {".js", ".jsx", ".ts", ".tsx", ".py", ".rb"}
            source_files = [f for f in self._find_files("*")
                          if os.path.splitext(f)[1].lower() in code_exts
                          and f not in test_files]
            ratio = len(test_files) / max(len(source_files), 1)

            if ratio < 0.1 and len(source_files) > 10:
                self._add(
                    id=self._next_id("TEST"),
                    severity="medium",
                    category="test_coverage",
                    title=f"Low test-to-source ratio ({len(test_files)} tests / {len(source_files)} source files)",
                    description=f"Test coverage appears minimal. Ratio: {ratio:.1%}.",
                    why_it_matters="While test count isn't everything, a very low ratio suggests large parts of the codebase are untested.",
                    recommendation="Focus on testing critical business logic and API endpoints first. UI component tests are lower priority for production readiness.",
                    effort_hours=8,
                )

    def _check_test_framework(self):
        deps = self.manifest.get("dependencies", {})
        all_deps = deps.get("node", []) + deps.get("python", [])
        all_deps_lower = [d.lower() for d in all_deps]

        detected_frameworks = []
        for fw_name, fw_deps in TEST_FRAMEWORKS.items():
            if any(d in all_deps_lower for d in fw_deps):
                detected_frameworks.append(fw_name)

        # Check for pytest in Python projects
        if self.manifest.get("primary_language") == "python":
            py_files = self._find_files("conftest.py", "pytest.ini", "setup.cfg", "pyproject.toml")
            for fp in py_files:
                content = self._read_file(fp)
                if content and "pytest" in content:
                    if "pytest" not in detected_frameworks:
                        detected_frameworks.append("pytest")

        if not detected_frameworks and self.manifest.get("test_file_count", 0) == 0:
            self._add(
                id=self._next_id("TEST"),
                severity="medium",
                category="test_framework",
                title="No test framework configured",
                description="No testing library (Jest, Vitest, Pytest, etc.) found in dependencies.",
                why_it_matters="Without a test framework, even writing tests requires setup first.",
                recommendation="Add Vitest (modern, fast, Vite-compatible) for TypeScript/JS or pytest for Python. Both have minimal setup.",
                effort_hours=1,
            )

    def _check_test_coverage_config(self):
        test_files = self.manifest.get("test_files", [])
        if not test_files:
            return

        # Look for coverage config
        coverage_signals = self._find_files(".nycrc", ".nycrc.json", "jest.config.*", "vitest.config.*",
                                             ".coveragerc", "setup.cfg", "pyproject.toml")
        has_coverage = False
        for fp in coverage_signals:
            content = self._read_file(fp)
            if content and ("coverage" in content.lower() or "collectCoverage" in content):
                has_coverage = True
                break

        if not has_coverage:
            self._add(
                id=self._next_id("TEST"),
                severity="low",
                category="test_coverage",
                title="No test coverage reporting configured",
                description="Tests exist but no coverage reporting is set up.",
                why_it_matters="Coverage reports show which code paths are untested. Without them, you're guessing about what's covered.",
                recommendation="Add coverage to your test command: 'vitest --coverage' or 'pytest --cov'. Track coverage trends over time.",
                effort_hours=1,
            )

    def _check_test_types(self):
        test_files = self.manifest.get("test_files", [])
        if not test_files:
            return

        has_unit = False
        has_integration = False
        has_e2e = False

        deps = self.manifest.get("dependencies", {})
        all_deps = deps.get("node", []) + deps.get("python", [])

        # E2E framework detection
        e2e_libs = {"cypress", "playwright", "@playwright/test", "selenium", "puppeteer"}
        has_e2e = any(lib in d for d in all_deps for lib in e2e_libs)

        # Check test file patterns
        for fp in test_files:
            fp_lower = fp.lower()
            if "e2e" in fp_lower or "end-to-end" in fp_lower or "integration" in fp_lower:
                has_integration = True
            if "unit" in fp_lower or ".test." in fp_lower or ".spec." in fp_lower:
                has_unit = True

        if has_unit and not has_e2e:
            distribution = self.context.get("distribution_target", "web")
            if distribution in ("web-saas", "app-store"):
                self._add(
                    id=self._next_id("TEST"),
                    severity="low",
                    category="test_types",
                    title="No end-to-end tests detected",
                    description="Unit/integration tests exist but no E2E testing framework (Playwright, Cypress) found.",
                    why_it_matters="E2E tests verify complete user flows. They catch issues that unit tests miss: broken forms, failed API integrations, rendering bugs.",
                    recommendation="Add Playwright for E2E testing. Start with 2-3 critical user flows (signup, core feature, payment).",
                    effort_hours=8,
                )

    def _check_test_scripts(self):
        # Check package.json for test script
        deps = self.manifest.get("dependencies", {})
        if deps.get("node"):
            pkg_content = self._read_file("package.json")
            if pkg_content:
                import json
                try:
                    pkg = json.loads(pkg_content)
                    scripts = pkg.get("scripts", {})
                    if "test" not in scripts:
                        self._add(
                            id=self._next_id("TEST"),
                            severity="low",
                            category="test_scripts",
                            title="No 'test' script in package.json",
                            description="package.json has no 'test' script defined.",
                            why_it_matters="A standardized 'npm test' command makes it easy for CI and other developers to run tests.",
                            recommendation="Add a test script: \"test\": \"vitest\" or \"test\": \"jest\".",
                            effort_hours=0.25,
                        )
                except json.JSONDecodeError:
                    pass

    def _check_test_quality(self):
        test_files = self.manifest.get("test_files", [])
        if len(test_files) < 3:
            return

        shallow_tests = 0
        for fp in test_files[:15]:
            content = self._read_file(fp)
            if not content:
                continue
            # Check for test files that only have snapshot tests or trivial assertions
            assertions = len(re.findall(r'(?:expect|assert|should)', content))
            test_cases = len(re.findall(r'(?:it\(|test\(|def test_)', content))
            if test_cases > 0 and assertions / test_cases < 1:
                shallow_tests += 1

        if shallow_tests > 3:
            self._add(
                id=self._next_id("TEST"),
                severity="low",
                category="test_quality",
                title=f"{shallow_tests} test files with low assertion density",
                description="Some test files have test cases with very few assertions, suggesting superficial testing.",
                why_it_matters="Tests that don't assert meaningful behavior give false confidence. A passing test suite isn't valuable if the tests don't check anything.",
                recommendation="Review test files with low assertions. Each test should verify a specific behavior with explicit assertions.",
                effort_hours=shallow_tests * 0.5,
            )
