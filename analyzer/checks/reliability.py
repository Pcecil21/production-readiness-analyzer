"""Reliability checks: error handling, health endpoints, graceful shutdown, retries."""

import re
from pathlib import Path

from analyzer.checks import BaseChecker
from analyzer.models import CategoryResult, Finding, Severity


class ReliabilityChecker(BaseChecker):
    def run(self) -> CategoryResult:
        findings: list[Finding] = []
        score = 100

        all_content = self._aggregate_source()

        # REL-001: Health check endpoint
        health_patterns = [
            r'/health', r'/healthz', r'/readyz', r'/livez',
            r'health[-_]?check', r'HealthCheck',
        ]
        has_health = any(re.search(p, all_content, re.IGNORECASE) for p in health_patterns)
        if not has_health:
            findings.append(Finding(
                check_id="REL-001",
                category="reliability",
                severity=Severity.CRITICAL,
                message="No health check endpoint detected — orchestrators can't verify service health",
            ))
            score -= 20

        # REL-002: Graceful shutdown handling
        shutdown_patterns = [
            r'SIGTERM', r'SIGINT', r'graceful.*shutdown', r'shutdown.*graceful',
            r'process\.on\([\'"]', r'signal\.Notify', r'atexit',
            r'@PreDestroy', r'ShutdownHook',
        ]
        has_shutdown = any(re.search(p, all_content) for p in shutdown_patterns)
        if not has_shutdown:
            findings.append(Finding(
                check_id="REL-002",
                category="reliability",
                severity=Severity.WARNING,
                message="No graceful shutdown handling detected — risk of dropped requests during deploys",
            ))
            score -= 15

        # REL-003: Retry / circuit breaker logic
        retry_patterns = [
            r'retry', r'retries', r'backoff', r'circuit.?breaker',
            r'tenacity', r'polly', r'resilience4j', r'hystrix',
        ]
        has_retry = any(re.search(p, all_content, re.IGNORECASE) for p in retry_patterns)
        if not has_retry:
            findings.append(Finding(
                check_id="REL-003",
                category="reliability",
                severity=Severity.INFO,
                message="No retry or circuit-breaker logic detected — external calls may fail without recovery",
            ))
            score -= 5

        # REL-004: Catch-all error handlers
        error_patterns = [
            r'catch\s*\(', r'except\s', r'rescue\s', r'recover\s*\(',
            r'errorHandler', r'error_handler', r'@ExceptionHandler',
            r'app\.use\(.*err',
        ]
        has_error_handling = any(re.search(p, all_content) for p in error_patterns)
        if not has_error_handling:
            findings.append(Finding(
                check_id="REL-004",
                category="reliability",
                severity=Severity.WARNING,
                message="No error handling patterns detected",
            ))
            score -= 15

        return CategoryResult(name="reliability", score=max(0, score), findings=findings)

    def _aggregate_source(self) -> str:
        """Concatenate source file contents for pattern scanning."""
        source_exts = {".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".php", ".cs", ".kt", ".swift"}
        parts = []
        for f in self.files:
            if f.suffix in source_exts:
                parts.append(self._read_safe(f, max_bytes=100_000))
        return "\n".join(parts)
