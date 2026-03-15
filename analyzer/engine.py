"""Core analysis engine that orchestrates all checkers."""

from pathlib import Path

from analyzer.models import AnalysisResult, CategoryResult
from analyzer.checks.security import SecurityChecker
from analyzer.checks.reliability import ReliabilityChecker
from analyzer.checks.observability import ObservabilityChecker
from analyzer.checks.testing import TestingChecker
from analyzer.checks.documentation import DocumentationChecker
from analyzer.checks.operations import OperationsChecker
from analyzer.checks.code_quality import CodeQualityChecker
from analyzer.checks.release import ReleaseChecker
from analyzer.checks.architecture import ArchitectureChecker
from analyzer.checks.accessibility import AccessibilityChecker
from analyzer.checks.api_design import ApiDesignChecker
from analyzer.checks.developer_experience import DeveloperExperienceChecker
from analyzer.checks.process import ProcessChecker

CHECKER_MAP = {
    "security": SecurityChecker,
    "reliability": ReliabilityChecker,
    "observability": ObservabilityChecker,
    "testing": TestingChecker,
    "documentation": DocumentationChecker,
    "operations": OperationsChecker,
    "code_quality": CodeQualityChecker,
    "release": ReleaseChecker,
    "architecture": ArchitectureChecker,
    "accessibility": AccessibilityChecker,
    "api_design": ApiDesignChecker,
    "developer_experience": DeveloperExperienceChecker,
    "process": ProcessChecker,
}


class AnalysisEngine:
    def __init__(self, target: Path, config: dict, categories: list[str]):
        self.target = target
        self.config = config
        self.categories = categories
        self.disabled_checks = set(config.get("disabled_checks", []))

    def _collect_files(self) -> list[Path]:
        """Walk the target directory, respecting exclusions."""
        excludes = self.config.get("exclude", [])
        files = []
        for p in self.target.rglob("*"):
            if not p.is_file():
                continue
            rel = str(p.relative_to(self.target)).replace("\\", "/")
            if any(self._matches_exclude(rel, ex) for ex in excludes):
                continue
            files.append(p)
        return files

    @staticmethod
    def _matches_exclude(rel_path: str, pattern: str) -> bool:
        """Simple exclusion matching — prefix or suffix."""
        pattern = pattern.rstrip("/")
        return rel_path.startswith(pattern) or f"/{pattern}/" in f"/{rel_path}/" or rel_path.startswith(f"{pattern}/")

    def run(self) -> AnalysisResult:
        files = self._collect_files()
        category_results: dict[str, CategoryResult] = {}

        for cat_name in self.categories:
            checker_cls = CHECKER_MAP.get(cat_name)
            if not checker_cls:
                continue
            checker = checker_cls(self.target, files, self.config)
            result = checker.run()
            # Filter disabled checks
            result.findings = [f for f in result.findings if f.check_id not in self.disabled_checks]
            category_results[cat_name] = result

        # Calculate overall score
        if category_results:
            overall = sum(r.score for r in category_results.values()) // len(category_results)
        else:
            overall = 0

        return AnalysisResult(
            project_name=self.target.name,
            overall_score=overall,
            categories=category_results,
        )
