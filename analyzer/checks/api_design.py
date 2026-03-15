"""API design checks — inspired by claude-api & review skills.

Validates API documentation, rate limiting, error response patterns,
authentication, and versioning.
"""

import re

from analyzer.checks import BaseChecker
from analyzer.models import CategoryResult, Finding, Severity

SOURCE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php", ".cs"}


class ApiDesignChecker(BaseChecker):
    def run(self) -> CategoryResult:
        findings: list[Finding] = []
        score = 100

        all_content = self._aggregate_source()

        # Detect if this is an API project
        api_indicators = [
            r'(app\.(get|post|put|patch|delete)|router\.(get|post|put|patch|delete))',
            r'@(Get|Post|Put|Patch|Delete|RequestMapping|ApiOperation)',
            r'http\.Handle', r'gin\.(GET|POST)', r'echo\.(GET|POST)',
            r'FastAPI|flask|express|koa|hapi|restify|django.*urls',
        ]
        is_api = any(re.search(p, all_content, re.IGNORECASE) for p in api_indicators)

        if not is_api:
            return CategoryResult(name="api_design", score=100, findings=[
                Finding(
                    check_id="API-000",
                    category="api_design",
                    severity=Severity.INFO,
                    message="No API framework detected — API design checks skipped",
                ),
            ])

        # API-001: OpenAPI / Swagger spec
        openapi_files = [f for f in self.files if any(
            kw in f.name.lower() for kw in ("openapi", "swagger", "api-spec", "api_spec")
        )]
        openapi_in_code = re.search(r'(openapi|swagger|@Api|apispec|drf-spectacular)', all_content, re.IGNORECASE)
        if not openapi_files and not openapi_in_code:
            findings.append(Finding(
                check_id="API-001",
                category="api_design",
                severity=Severity.WARNING,
                message="No OpenAPI/Swagger specification — API consumers have no contract to code against",
            ))
            score -= 15

        # API-002: Rate limiting
        rate_limit_patterns = [
            r'rate.?limit', r'throttl', r'express-rate-limit',
            r'slowapi', r'ratelimit', r'bucket', r'leaky.?bucket',
            r'token.?bucket', r'X-RateLimit',
        ]
        has_rate_limit = any(re.search(p, all_content, re.IGNORECASE) for p in rate_limit_patterns)
        if not has_rate_limit:
            findings.append(Finding(
                check_id="API-002",
                category="api_design",
                severity=Severity.WARNING,
                message="No rate limiting detected — API is vulnerable to abuse and resource exhaustion",
            ))
            score -= 15

        # API-003: Authentication / authorization
        auth_patterns = [
            r'auth', r'jwt', r'oauth', r'bearer', r'passport',
            r'session', r'cookie', r'token', r'middleware.*auth',
            r'@Authenticated', r'@RequiresPermission', r'IsAuthenticated',
        ]
        has_auth = any(re.search(p, all_content, re.IGNORECASE) for p in auth_patterns)
        if not has_auth:
            findings.append(Finding(
                check_id="API-003",
                category="api_design",
                severity=Severity.CRITICAL,
                message="No authentication/authorization patterns detected — API may be fully open",
            ))
            score -= 20

        # API-004: Consistent error response format
        error_format_patterns = [
            r'error.*response', r'ApiError', r'HttpException',
            r'error_handler', r'errorHandler', r'@exception_handler',
            r'problem\+json', r'ErrorResponse',
        ]
        has_error_format = any(re.search(p, all_content) for p in error_format_patterns)
        if not has_error_format:
            findings.append(Finding(
                check_id="API-004",
                category="api_design",
                severity=Severity.INFO,
                message="No standardized error response format detected — consumers will struggle with inconsistent errors",
            ))
            score -= 5

        # API-005: Input validation
        validation_patterns = [
            r'(validate|validator|validation|joi|yup|zod|cerberus|marshmallow)',
            r'@Valid', r'class-validator', r'express-validator',
            r'pydantic', r'@Body\(', r'schema\.validate',
        ]
        has_validation = any(re.search(p, all_content, re.IGNORECASE) for p in validation_patterns)
        if not has_validation:
            findings.append(Finding(
                check_id="API-005",
                category="api_design",
                severity=Severity.WARNING,
                message="No input validation library detected — APIs should validate all incoming data",
            ))
            score -= 10

        # API-006: CORS configuration
        cors_patterns = [r'cors', r'Access-Control-Allow', r'@CrossOrigin']
        has_cors = any(re.search(p, all_content, re.IGNORECASE) for p in cors_patterns)
        if not has_cors:
            findings.append(Finding(
                check_id="API-006",
                category="api_design",
                severity=Severity.INFO,
                message="No CORS configuration detected — cross-origin requests may be blocked or too permissive",
            ))
            score -= 5

        # API-007: Pagination support
        pagination_patterns = [
            r'pagina', r'page_size', r'pageSize', r'per_page', r'perPage',
            r'limit.*offset', r'cursor', r'next_token',
        ]
        has_pagination = any(re.search(p, all_content, re.IGNORECASE) for p in pagination_patterns)
        if not has_pagination:
            findings.append(Finding(
                check_id="API-007",
                category="api_design",
                severity=Severity.INFO,
                message="No pagination pattern detected — list endpoints may return unbounded result sets",
            ))
            score -= 5

        return CategoryResult(name="api_design", score=max(0, score), findings=findings)

    def _aggregate_source(self) -> str:
        parts = []
        for f in self.files:
            if f.suffix in SOURCE_EXTS:
                parts.append(self._read_safe(f, max_bytes=100_000))
        return "\n".join(parts)
