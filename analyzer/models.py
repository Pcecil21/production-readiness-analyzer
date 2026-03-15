"""Data models for analysis results."""

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Finding:
    check_id: str
    category: str
    severity: Severity
    message: str
    file: str | None = None
    line: int | None = None

    def to_dict(self) -> dict:
        d = {
            "check_id": self.check_id,
            "category": self.category,
            "severity": self.severity.value,
            "message": self.message,
        }
        if self.file:
            d["file"] = self.file
        if self.line:
            d["line"] = self.line
        return d


@dataclass
class CategoryResult:
    name: str
    score: int  # 0-100
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "score": self.score,
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class AnalysisResult:
    project_name: str
    overall_score: int
    categories: dict[str, CategoryResult] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "overall_score": self.overall_score,
            "categories": {k: v.to_dict() for k, v in self.categories.items()},
        }

    @property
    def critical_findings(self) -> list[Finding]:
        findings = []
        for cat in self.categories.values():
            findings.extend(f for f in cat.findings if f.severity == Severity.CRITICAL)
        return findings

    @property
    def warnings(self) -> list[Finding]:
        findings = []
        for cat in self.categories.values():
            findings.extend(f for f in cat.findings if f.severity == Severity.WARNING)
        return findings
