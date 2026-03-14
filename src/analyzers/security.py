"""Security analyzer — secrets, auth, input validation, CORS, data handling."""

from __future__ import annotations
import os
import re
from .base import BaseAnalyzer


# Patterns that strongly suggest hardcoded secrets
SECRET_PATTERNS = [
    (r'(?:api[_-]?key|apikey)\s*[:=]\s*["\']([A-Za-z0-9_\-]{20,})["\']', "API key"),
    (r'(?:secret|password|passwd|pwd)\s*[:=]\s*["\']([^"\']{8,})["\']', "Secret/password"),
    (r'(?:token)\s*[:=]\s*["\']([A-Za-z0-9_\-\.]{20,})["\']', "Token"),
    (r'sk[_-](?:live|test)[_-][A-Za-z0-9]{20,}', "Stripe secret key"),
    (r'sk-[A-Za-z0-9]{40,}', "OpenAI API key"),
    (r'ghp_[A-Za-z0-9]{36}', "GitHub personal access token"),
    (r'AKIA[A-Z0-9]{16}', "AWS access key"),
    (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "Private key"),
]

# Files where secrets are expected (env templates, docs)
SECRET_WHITELIST_FILES = {".env.example", ".env.template", ".env.sample", "config.example.yaml",
                          "config.example.json", "config.sample.yaml"}

CODE_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".py", ".rb", ".go", ".rs", ".java", ".kt", ".swift", ".php"}


class SecurityAnalyzer(BaseAnalyzer):
    name = "security"
    description = "Hardcoded secrets, auth patterns, input validation, CORS, data handling"

    def run(self) -> list:
        self._check_hardcoded_secrets()
        self._check_env_gitignore()
        self._check_auth_presence()
        self._check_input_validation()
        self._check_cors()
        self._check_sensitive_data_exposure()
        self._check_dependency_vulnerabilities()
        self._check_https_enforcement()
        return self.findings

    def _check_hardcoded_secrets(self):
        code_files = [f for f in self._find_files("*") if os.path.splitext(f)[1].lower() in CODE_EXTENSIONS]
        for fp in code_files:
            if os.path.basename(fp) in SECRET_WHITELIST_FILES:
                continue
            content = self._read_file(fp)
            if not content:
                continue
            for line_num, line in enumerate(content.splitlines(), 1):
                if line.strip().startswith("//") or line.strip().startswith("#"):
                    continue
                for pattern, secret_type in SECRET_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        self._add(
                            id=self._next_id("SEC"),
                            severity="critical",
                            category="hardcoded_secrets",
                            title=f"Possible hardcoded {secret_type} in {fp}",
                            file=fp,
                            line=line_num,
                            description=f"Line contains what appears to be a hardcoded {secret_type}.",
                            why_it_matters="Secrets in source code can be extracted from git history, client bundles, or leaked repos. This is the #1 cause of production security incidents.",
                            recommendation=f"Move to environment variable. Add to .env and ensure .env is in .gitignore. If this was ever committed, rotate the secret immediately.",
                            effort_hours=0.5,
                        )
                        break  # one finding per line

    def _check_env_gitignore(self):
        env_files = self.manifest.get("env_files", [])
        gitignore = self.manifest.get("gitignore", {})
        entries = gitignore.get("entries", [])

        if not gitignore.get("exists"):
            self._add(
                id=self._next_id("SEC"),
                severity="high",
                category="gitignore",
                title="No .gitignore file found",
                description="Without .gitignore, sensitive files like .env, node_modules, and build artifacts may be committed.",
                why_it_matters="Accidentally committing .env files or node_modules is extremely common and can expose secrets or bloat the repo.",
                recommendation="Create a .gitignore appropriate for your stack. Use gitignore.io for templates.",
                effort_hours=0.25,
            )
            return

        env_covered = any(e in entries for e in [".env", ".env*", ".env.local", "*.env"])
        if env_files and not env_covered:
            self._add(
                id=self._next_id("SEC"),
                severity="critical",
                category="gitignore",
                title=".env files exist but may not be gitignored",
                description=f"Found env files: {', '.join(env_files)}. .gitignore does not appear to exclude .env patterns.",
                why_it_matters="If .env files are committed, anyone with repo access can see your secrets. Even private repos can be leaked.",
                recommendation="Add '.env*' to .gitignore. Check git history: if .env was ever committed, rotate all secrets in it.",
                effort_hours=0.25,
            )

    def _check_auth_presence(self):
        auth_detected = self.manifest.get("auth", [])
        distribution = self.context.get("distribution_target", "web")
        has_api_routes = bool(self._find_files("*/api/*", "*/routes/*", "*/controllers/*"))

        if not auth_detected and has_api_routes:
            severity = "critical" if distribution in ("web-saas", "app-store") else "high"
            self._add(
                id=self._next_id("SEC"),
                severity=severity,
                category="authentication",
                title="No authentication library or pattern detected",
                description="The app has API routes but no recognized auth library (NextAuth, Clerk, Supabase Auth, Passport, etc.).",
                why_it_matters=f"For a {distribution} product, unauthenticated API routes mean anyone can access or modify data.",
                recommendation="Add authentication before going to production. For Next.js: NextAuth or Clerk. For Express: Passport. For Supabase: enable RLS + Supabase Auth.",
                effort_hours=8,
            )

    def _check_input_validation(self):
        api_files = self._find_files("*/api/*", "*/routes/*", "*/controllers/*", "*/endpoints/*")
        if not api_files:
            return

        validation_libs = {"zod", "yup", "joi", "class-validator", "express-validator",
                           "pydantic", "marshmallow", "cerberus", "ajv"}
        deps = self.manifest.get("dependencies", {})
        all_deps = deps.get("node", []) + deps.get("python", [])
        has_validation_lib = any(v in d.lower() for d in all_deps for v in validation_libs)

        if not has_validation_lib:
            # Check for inline validation patterns
            has_inline = False
            for fp in api_files[:10]:  # sample first 10
                content = self._read_file(fp)
                if content and re.search(r'(?:typeof|instanceof|\.length|parseInt|isNaN|validate|sanitize)', content):
                    has_inline = True
                    break

            if not has_inline:
                self._add(
                    id=self._next_id("SEC"),
                    severity="high",
                    category="input_validation",
                    title="No input validation detected on API routes",
                    description=f"Found {len(api_files)} API route files but no validation library and no inline validation patterns.",
                    why_it_matters="Unvalidated input is the root cause of injection attacks, data corruption, and crashes. This is OWASP Top 10 #1.",
                    recommendation="Add a validation library (Zod for TypeScript, Pydantic for Python) and validate all request inputs at the API boundary.",
                    effort_hours=4,
                    depends_on=[],
                )

    def _check_cors(self):
        # Look for CORS configuration
        code_files = self._find_files("*.ts", "*.tsx", "*.js", "*.jsx", "*.py")
        cors_found = False
        wildcard_cors = False

        for fp in code_files:
            content = self._read_file(fp)
            if not content:
                continue
            if "cors" in content.lower():
                cors_found = True
                if re.search(r'origin\s*:\s*["\'\*]?\*', content) or "Access-Control-Allow-Origin: *" in content:
                    wildcard_cors = True
                    self._add(
                        id=self._next_id("SEC"),
                        severity="medium",
                        category="cors",
                        title=f"Wildcard CORS origin in {fp}",
                        file=fp,
                        description="CORS is configured to allow all origins (*).",
                        why_it_matters="Wildcard CORS allows any website to make authenticated requests to your API if credentials are included.",
                        recommendation="Restrict CORS origins to your actual frontend domains. Use an allowlist, not a wildcard.",
                        effort_hours=1,
                    )
                break

        has_api = bool(self._find_files("*/api/*"))
        if has_api and not cors_found:
            self._add(
                id=self._next_id("SEC"),
                severity="info",
                category="cors",
                title="No explicit CORS configuration found",
                description="API routes exist but no CORS setup was detected. This may be fine if your API and frontend are same-origin.",
                why_it_matters="If you add a separate frontend or mobile app later, you'll need CORS. Not urgent if everything is same-origin.",
                recommendation="Add CORS config when your API serves non-same-origin clients. For Next.js API routes, same-origin is the default.",
                effort_hours=1,
            )

    def _check_sensitive_data_exposure(self):
        # Check for logging patterns that might expose sensitive data
        code_files = self._find_files("*.ts", "*.tsx", "*.js", "*.jsx", "*.py")
        for fp in code_files[:20]:
            content = self._read_file(fp)
            if not content:
                continue
            for line_num, line in enumerate(content.splitlines(), 1):
                if re.search(r'console\.log\(.*(?:password|token|secret|key|credential)', line, re.IGNORECASE):
                    self._add(
                        id=self._next_id("SEC"),
                        severity="medium",
                        category="data_exposure",
                        title=f"Possible sensitive data in console.log in {fp}",
                        file=fp,
                        line=line_num,
                        description="A console.log statement appears to output sensitive data.",
                        why_it_matters="Console logs persist in browser dev tools and server logs. Sensitive data in logs can be accessed by anyone with log access.",
                        recommendation="Remove sensitive data from log statements. Use a structured logger that automatically redacts sensitive fields.",
                        effort_hours=0.5,
                    )
                    break  # one per file

    def _check_dependency_vulnerabilities(self):
        # We can't run npm audit, but we can flag the need
        deps = self.manifest.get("dependencies", {})
        total = deps.get("total_count", 0)
        if total > 0:
            self._add(
                id=self._next_id("SEC"),
                severity="info",
                category="dependency_security",
                title=f"Run dependency audit ({total} dependencies)",
                description=f"Project has {total} dependencies. Run 'npm audit' or 'pip audit' to check for known vulnerabilities.",
                why_it_matters="Known vulnerabilities in dependencies are the easiest attack vector. Automated scanning catches low-hanging fruit.",
                recommendation="Run 'npm audit fix' (Node) or 'pip-audit' (Python). Set up Dependabot or Renovate for ongoing monitoring.",
                effort_hours=1,
            )

    def _check_https_enforcement(self):
        code_files = self._find_files("*.ts", "*.tsx", "*.js", "*.jsx", "*.py")
        for fp in code_files[:30]:
            content = self._read_file(fp)
            if not content:
                continue
            http_urls = re.findall(r'http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)[^\s"\']+', content)
            if http_urls:
                self._add(
                    id=self._next_id("SEC"),
                    severity="medium",
                    category="https",
                    title=f"Non-HTTPS URL found in {fp}",
                    file=fp,
                    description=f"Found HTTP (not HTTPS) URL: {http_urls[0][:60]}...",
                    why_it_matters="HTTP traffic can be intercepted. All production API calls and resource loads should use HTTPS.",
                    recommendation="Replace http:// with https:// for all external URLs.",
                    effort_hours=0.25,
                )
                break  # one finding is enough to flag the pattern
