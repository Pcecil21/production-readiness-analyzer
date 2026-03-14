"""Infrastructure analyzer — deployment, CI/CD, monitoring, backups, env management."""

from __future__ import annotations
import os
from .base import BaseAnalyzer


class InfrastructureAnalyzer(BaseAnalyzer):
    name = "infrastructure"
    description = "Deployment, CI/CD, monitoring, logging, backups, environment management"

    def run(self) -> list:
        self._check_deployment()
        self._check_ci_cd()
        self._check_monitoring()
        self._check_logging()
        self._check_env_management()
        self._check_database_migrations()
        self._check_backup_strategy()
        self._check_error_tracking()
        self._check_health_endpoint()
        return self.findings

    def _check_deployment(self):
        deployment = self.manifest.get("deployment", [])
        if not deployment:
            self._add(
                id=self._next_id("INFRA"),
                severity="high",
                category="deployment",
                title="No deployment configuration detected",
                description="No Vercel, Netlify, Docker, AWS, or other deployment config found.",
                why_it_matters="Without deployment config, there's no repeatable way to ship to production. Manual deploys are error-prone and not scalable.",
                recommendation="Choose a deployment target. For Next.js: Vercel (easiest) or Docker. For Python: Railway, Fly.io, or Docker on any cloud.",
                effort_hours=4,
            )
        elif "docker" in deployment:
            # Check Dockerfile quality
            dockerfile = self._read_file("Dockerfile")
            if dockerfile:
                issues = []
                if "FROM node:" in dockerfile and ":latest" in dockerfile:
                    issues.append("Uses :latest tag (pin a specific version)")
                if "npm install" in dockerfile and "npm ci" not in dockerfile:
                    issues.append("Uses 'npm install' instead of 'npm ci' (non-deterministic)")
                if ".dockerignore" not in [os.path.basename(f) for f in self._find_files(".dockerignore")]:
                    issues.append("No .dockerignore file (may copy node_modules/secrets into image)")
                if issues:
                    self._add(
                        id=self._next_id("INFRA"),
                        severity="medium",
                        category="deployment",
                        title="Dockerfile quality issues",
                        file="Dockerfile",
                        description="Issues: " + "; ".join(issues),
                        why_it_matters="Dockerfile issues lead to non-reproducible builds, bloated images, or accidentally baked-in secrets.",
                        recommendation="Pin base image versions, use 'npm ci', add .dockerignore, use multi-stage builds.",
                        effort_hours=2,
                    )

    def _check_ci_cd(self):
        ci_cd = self.manifest.get("ci_cd", [])
        if not ci_cd:
            self._add(
                id=self._next_id("INFRA"),
                severity="high",
                category="ci_cd",
                title="No CI/CD pipeline detected",
                description="No GitHub Actions, GitLab CI, CircleCI, or other CI config found.",
                why_it_matters="Without CI/CD, every deploy is manual and untested. Bugs reach production faster, and rollbacks are painful.",
                recommendation="Add GitHub Actions at minimum: lint + type-check + test on every PR. Add auto-deploy to staging on merge to main.",
                effort_hours=4,
                depends_on=[],
            )
        else:
            # Check if CI actually runs tests
            if "github-actions" in ci_cd:
                workflow_files = self._find_files(".github/workflows/*.yml", ".github/workflows/*.yaml")
                has_test_step = False
                for wf in workflow_files:
                    content = self._read_file(wf)
                    if content and ("test" in content.lower() or "jest" in content.lower() or "pytest" in content.lower()):
                        has_test_step = True
                        break
                if not has_test_step:
                    self._add(
                        id=self._next_id("INFRA"),
                        severity="medium",
                        category="ci_cd",
                        title="CI pipeline exists but may not run tests",
                        description="GitHub Actions workflow found but no test step detected.",
                        why_it_matters="A CI pipeline that doesn't run tests provides false confidence. It's better than nothing, but not by much.",
                        recommendation="Add a test step to your workflow. Even 'npm test' or 'pytest' as a start.",
                        effort_hours=1,
                    )

    def _check_monitoring(self):
        deps = self.manifest.get("dependencies", {})
        all_deps = deps.get("node", []) + deps.get("python", [])
        all_deps_lower = [d.lower() for d in all_deps]

        monitoring_libs = {"@sentry/nextjs", "@sentry/node", "@sentry/react", "sentry-sdk",
                           "newrelic", "datadog", "@datadog/browser-rum",
                           "prom-client", "prometheus_client",
                           "@opentelemetry/sdk-node", "opentelemetry",
                           "applicationinsights"}

        has_monitoring = any(m in d for d in all_deps_lower for m in monitoring_libs)
        if not has_monitoring:
            self._add(
                id=self._next_id("INFRA"),
                severity="high",
                category="monitoring",
                title="No monitoring or error tracking service detected",
                description="No Sentry, DataDog, New Relic, or OpenTelemetry dependency found.",
                why_it_matters="Without monitoring, you won't know when your app is broken until users tell you (or leave). In production, you need visibility.",
                recommendation="Add Sentry (free tier is generous) for error tracking at minimum. Add uptime monitoring (UptimeRobot, free) for health checks.",
                effort_hours=3,
            )

    def _check_logging(self):
        deps = self.manifest.get("dependencies", {})
        all_deps = deps.get("node", []) + deps.get("python", [])
        all_deps_lower = [d.lower() for d in all_deps]

        logging_libs = {"winston", "pino", "bunyan", "morgan", "loglevel",
                        "loguru", "structlog", "python-json-logger"}
        has_structured_logging = any(lib in d for d in all_deps_lower for lib in logging_libs)

        if not has_structured_logging:
            # Check for console.log usage as proxy
            code_files = self._find_files("*.ts", "*.tsx", "*.js", "*.jsx", "*.py")
            console_count = 0
            for fp in code_files[:20]:
                content = self._read_file(fp)
                if content:
                    console_count += content.count("console.log")
                    console_count += content.count("print(")

            if console_count > 10:
                self._add(
                    id=self._next_id("INFRA"),
                    severity="medium",
                    category="logging",
                    title="Using console.log/print instead of structured logging",
                    description=f"Found {console_count}+ console.log/print statements but no structured logging library.",
                    why_it_matters="console.log is fine for development but not searchable or filterable in production. When debugging a production issue at 2am, you need structured logs.",
                    recommendation="Add pino (Node) or structlog (Python). Replace console.log in API routes and server code. Client-side console.log is less critical.",
                    effort_hours=4,
                )

    def _check_env_management(self):
        env_vars = self.manifest.get("env_vars_referenced", [])
        env_files = self.manifest.get("env_files", [])

        if env_vars and not env_files:
            self._add(
                id=self._next_id("INFRA"),
                severity="medium",
                category="env_management",
                title="Code references env vars but no .env file found",
                description=f"Code references {len(env_vars)} env vars ({', '.join(env_vars[:5])}...) but no .env file exists.",
                why_it_matters="Without a .env file or .env.example, new developers (or your future self) won't know which env vars are needed to run the app.",
                recommendation="Create a .env.example with all required vars (using placeholder values) and document them.",
                effort_hours=1,
            )

        if len(env_vars) > 0:
            # Check for env validation
            deps = self.manifest.get("dependencies", {})
            all_deps = deps.get("node", []) + deps.get("python", [])
            env_validation_libs = {"envalid", "@t3-oss/env-nextjs", "dotenv-safe", "pydantic-settings"}
            has_env_validation = any(lib in d for d in all_deps for lib in env_validation_libs)

            if not has_env_validation and len(env_vars) > 3:
                self._add(
                    id=self._next_id("INFRA"),
                    severity="medium",
                    category="env_management",
                    title="No environment variable validation",
                    description=f"App uses {len(env_vars)} env vars but no validation library ensures they're set at startup.",
                    why_it_matters="Missing env vars cause cryptic runtime errors. Validation at startup fails fast with a clear message instead of crashing hours later.",
                    recommendation="Add envalid (Node) or pydantic-settings (Python) to validate env vars on startup.",
                    effort_hours=2,
                )

    def _check_database_migrations(self):
        databases = self.manifest.get("databases", [])
        if not databases:
            return

        migration_signals = self._find_files("*/migrations/*", "*/migrate/*", "prisma/migrations/*",
                                              "drizzle/*", "alembic/*", "db/migrate/*")
        deps = self.manifest.get("dependencies", {})
        all_deps = deps.get("node", []) + deps.get("python", [])
        migration_tools = {"prisma", "@prisma/client", "drizzle-kit", "knex", "typeorm",
                           "alembic", "django", "sequelize-cli"}
        has_migration_tool = any(t in d for d in all_deps for t in migration_tools)

        # Supabase uses its own migration system
        if "supabase" in databases:
            supabase_migrations = self._find_files("supabase/migrations/*")
            if supabase_migrations:
                return
            has_migration_tool = True  # Supabase dashboard handles schema

        if not migration_signals and not has_migration_tool:
            self._add(
                id=self._next_id("INFRA"),
                severity="high",
                category="database",
                title="No database migration strategy detected",
                description=f"Using {', '.join(databases)} but no migration files or tools found.",
                why_it_matters="Without migrations, schema changes require manual SQL and can't be tracked, rolled back, or applied consistently across environments.",
                recommendation="Add a migration tool. Prisma (Node + SQL), Alembic (Python + SQL), or use Supabase's built-in migration CLI.",
                effort_hours=6,
            )

    def _check_backup_strategy(self):
        distribution = self.context.get("distribution_target", "web")
        databases = self.manifest.get("databases", [])

        if databases and distribution in ("web-saas", "app-store", "api"):
            # Check for backup config or documentation
            backup_files = self._find_files("*backup*", "*dump*")
            if not backup_files:
                self._add(
                    id=self._next_id("INFRA"),
                    severity="high",
                    category="backup",
                    title="No database backup strategy detected",
                    description="No backup scripts, dump files, or backup configuration found.",
                    why_it_matters="Data loss in production is catastrophic and often unrecoverable. Managed services (Supabase, PlanetScale) have automatic backups, but you should verify and test restores.",
                    recommendation="If using a managed DB (Supabase, PlanetScale): verify automatic backups are enabled and test a restore. If self-hosted: set up automated pg_dump/mysqldump + offsite storage.",
                    effort_hours=3,
                )

    def _check_error_tracking(self):
        # Check for error boundary in React apps
        frameworks = self.manifest.get("frameworks", [])
        if any(f in frameworks for f in ["react", "next.js"]):
            code_files = self._find_files("*.tsx", "*.jsx")
            has_error_boundary = False
            for fp in code_files[:30]:
                content = self._read_file(fp)
                if content and ("ErrorBoundary" in content or "componentDidCatch" in content or "error.tsx" in fp or "error.jsx" in fp):
                    has_error_boundary = True
                    break
            if not has_error_boundary:
                self._add(
                    id=self._next_id("INFRA"),
                    severity="medium",
                    category="error_handling",
                    title="No React Error Boundary detected",
                    description="No ErrorBoundary component or Next.js error.tsx file found.",
                    why_it_matters="Without error boundaries, a single component crash takes down the entire page. Users see a white screen with no recovery path.",
                    recommendation="Add error.tsx in your app directory (Next.js) or wrap key sections in ErrorBoundary components.",
                    effort_hours=2,
                )

    def _check_health_endpoint(self):
        api_files = self._find_files("*/api/*", "*/routes/*")
        has_health = False
        for fp in api_files:
            if "health" in fp.lower() or "status" in fp.lower() or "ping" in fp.lower():
                has_health = True
                break

        distribution = self.context.get("distribution_target", "web")
        if api_files and not has_health and distribution in ("web-saas", "api"):
            self._add(
                id=self._next_id("INFRA"),
                severity="medium",
                category="health_check",
                title="No health check endpoint found",
                description="No /health, /status, or /ping endpoint detected.",
                why_it_matters="Health endpoints are essential for load balancers, uptime monitors, and deployment systems to verify your app is running.",
                recommendation="Add a /api/health endpoint that returns 200 OK. Include basic checks (DB connectivity, etc.) for deeper health verification.",
                effort_hours=1,
            )
