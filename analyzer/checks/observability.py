"""Observability checks: logging, metrics, tracing, alerting."""

import re

from analyzer.checks import BaseChecker
from analyzer.models import CategoryResult, Finding, Severity


class ObservabilityChecker(BaseChecker):
    def run(self) -> CategoryResult:
        findings: list[Finding] = []
        score = 100

        all_content = self._aggregate()

        # OBS-001: Structured logging
        structured_log_patterns = [
            r'structlog', r'winston', r'pino', r'bunyan', r'zap\.', r'zerolog',
            r'logrus', r'slog\.', r'log4j2?', r'serilog', r'json.*log',
        ]
        has_structured = any(re.search(p, all_content, re.IGNORECASE) for p in structured_log_patterns)
        if not has_structured:
            findings.append(Finding(
                check_id="OBS-001",
                category="observability",
                severity=Severity.WARNING,
                message="No structured logging library detected — logs may not be machine-parsable",
            ))
            score -= 15

        # OBS-002: Metrics endpoint / library
        metrics_patterns = [
            r'prometheus', r'/metrics', r'statsd', r'datadog',
            r'opentelemetry', r'micrometer', r'newrelic',
            r'app_insights', r'cloudwatch.*metric',
        ]
        has_metrics = any(re.search(p, all_content, re.IGNORECASE) for p in metrics_patterns)
        if not has_metrics:
            findings.append(Finding(
                check_id="OBS-002",
                category="observability",
                severity=Severity.WARNING,
                message="No metrics library or endpoint detected — no quantitative visibility into service health",
            ))
            score -= 20

        # OBS-003: Distributed tracing
        tracing_patterns = [
            r'opentelemetry', r'jaeger', r'zipkin', r'x-ray',
            r'trace[-_]?id', r'span[-_]?id', r'dd-trace',
        ]
        has_tracing = any(re.search(p, all_content, re.IGNORECASE) for p in tracing_patterns)
        if not has_tracing:
            findings.append(Finding(
                check_id="OBS-003",
                category="observability",
                severity=Severity.INFO,
                message="No distributed tracing detected — cross-service debugging will be difficult",
            ))
            score -= 10

        # OBS-004: Alerting config
        alert_patterns = [
            r'alert', r'pagerduty', r'opsgenie', r'slack.*webhook',
            r'alertmanager',
        ]
        alert_files = [f for f in self.files if "alert" in f.name.lower()]
        has_alerting = bool(alert_files) or any(re.search(p, all_content, re.IGNORECASE) for p in alert_patterns)
        if not has_alerting:
            findings.append(Finding(
                check_id="OBS-004",
                category="observability",
                severity=Severity.WARNING,
                message="No alerting configuration detected",
            ))
            score -= 10

        return CategoryResult(name="observability", score=max(0, score), findings=findings)

    def _aggregate(self) -> str:
        source_exts = {
            ".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".php",
            ".yml", ".yaml", ".toml", ".json", ".tf", ".hcl",
        }
        parts = []
        for f in self.files:
            if f.suffix in source_exts:
                parts.append(self._read_safe(f, max_bytes=100_000))
        return "\n".join(parts)
