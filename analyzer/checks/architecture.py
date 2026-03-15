"""Architecture checks — inspired by plan-eng-review & plan-ceo-review skills.

Evaluates architectural decision records, separation of concerns, dependency
management, configuration patterns, and design documentation.
"""

import re
from pathlib import Path

from analyzer.checks import BaseChecker
from analyzer.models import CategoryResult, Finding, Severity

SOURCE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php", ".cs", ".kt"}


class ArchitectureChecker(BaseChecker):
    def run(self) -> CategoryResult:
        findings: list[Finding] = []
        score = 100

        all_content = self._aggregate_source()
        file_names = {f.name for f in self.files}
        rel_paths = [self._rel(f) for f in self.files]

        # ARC-001: Architecture Decision Records
        adr_files = [f for f in self.files if "adr" in str(f).lower() and f.suffix == ".md"]
        if not adr_files:
            findings.append(Finding(
                check_id="ARC-001",
                category="architecture",
                severity=Severity.INFO,
                message="No Architecture Decision Records (ADRs) — design rationale will be lost over time",
            ))
            score -= 5

        # ARC-002: Separation of concerns — check for layered structure
        layer_indicators = {
            "controllers": ["controller", "handler", "route", "endpoint", "api"],
            "services": ["service", "usecase", "interactor", "domain"],
            "data": ["repository", "model", "schema", "migration", "dao", "entity"],
        }
        layers_found = 0
        for layer, keywords in layer_indicators.items():
            if any(any(kw in p.lower() for kw in keywords) for p in rel_paths):
                layers_found += 1
        source_files = [f for f in self.files if f.suffix in SOURCE_EXTS]
        if len(source_files) > 10 and layers_found < 2:
            findings.append(Finding(
                check_id="ARC-002",
                category="architecture",
                severity=Severity.WARNING,
                message="No clear layered architecture detected — controllers, services, and data layers should be separated",
            ))
            score -= 10

        # ARC-003: Circular dependency signals (co-imports between same-level modules)
        # Lightweight heuristic: check if files import each other
        import_pairs = self._detect_circular_imports()
        if import_pairs:
            findings.append(Finding(
                check_id="ARC-003",
                category="architecture",
                severity=Severity.WARNING,
                message=f"Potential circular imports detected between {len(import_pairs)} file pair(s)",
            ))
            score -= 10

        # ARC-004: Configuration management
        config_patterns = [
            r'env\.(get|fetch|read)', r'os\.environ', r'process\.env',
            r'config\.(get|load|read)', r'Settings\(\)', r'dotenv',
            r'viper\.', r'configparser',
        ]
        has_config_mgmt = any(re.search(p, all_content) for p in config_patterns)
        env_example = any(f.name in (".env.example", ".env.template", ".env.sample") for f in self.files)
        if not has_config_mgmt:
            findings.append(Finding(
                check_id="ARC-004",
                category="architecture",
                severity=Severity.INFO,
                message="No environment-based configuration management detected",
            ))
            score -= 5
        elif not env_example:
            findings.append(Finding(
                check_id="ARC-004",
                category="architecture",
                severity=Severity.INFO,
                message="Environment config used but no .env.example template for onboarding",
            ))
            score -= 3

        # ARC-005: Database migration management
        migration_indicators = [
            "migration", "migrate", "alembic", "flyway", "knex",
            "prisma", "sequelize", "typeorm", "django",
        ]
        has_migrations = any(
            any(ind in str(f).lower() for ind in migration_indicators)
            for f in self.files
        )
        has_db = any(
            re.search(r'(database|postgres|mysql|sqlite|mongo|redis|dynamodb)', all_content, re.IGNORECASE)
            for _ in [1]
        )
        if has_db and not has_migrations:
            findings.append(Finding(
                check_id="ARC-005",
                category="architecture",
                severity=Severity.WARNING,
                message="Database usage detected but no migration framework — schema changes will be error-prone",
            ))
            score -= 10

        # ARC-006: API versioning
        api_version_patterns = [r'/v\d+/', r'/api/v\d', r'api[-_]?version', r'Accept-Version']
        has_api = re.search(r'(route|endpoint|api|router|controller)', all_content, re.IGNORECASE)
        has_versioning = any(re.search(p, all_content) for p in api_version_patterns)
        if has_api and not has_versioning:
            findings.append(Finding(
                check_id="ARC-006",
                category="architecture",
                severity=Severity.INFO,
                message="API detected but no versioning scheme — breaking changes will affect all consumers",
            ))
            score -= 5

        # ARC-007: Dependency injection / inversion of control
        di_patterns = [
            r'@Inject', r'@Injectable', r'inject\(', r'container\.resolve',
            r'dependency_injector', r'wire\.Build', r'providers\.',
        ]
        has_di = any(re.search(p, all_content) for p in di_patterns)
        if len(source_files) > 20 and not has_di:
            findings.append(Finding(
                check_id="ARC-007",
                category="architecture",
                severity=Severity.INFO,
                message="No dependency injection pattern detected in a large codebase — testing and modularity may suffer",
            ))
            score -= 5

        return CategoryResult(name="architecture", score=max(0, score), findings=findings)

    def _aggregate_source(self) -> str:
        parts = []
        for f in self.files:
            if f.suffix in SOURCE_EXTS:
                parts.append(self._read_safe(f, max_bytes=100_000))
        return "\n".join(parts)

    def _detect_circular_imports(self) -> list[tuple[str, str]]:
        """Lightweight circular import detection via mutual import scanning."""
        import_map: dict[str, set[str]] = {}
        py_files = [f for f in self.files if f.suffix == ".py"]

        for f in py_files:
            content = self._read_safe(f, max_bytes=50_000)
            rel = self._rel(f)
            imports = set()
            for m in re.finditer(r'(?:from|import)\s+([\w.]+)', content):
                imports.add(m.group(1))
            import_map[rel] = imports

        # Check for A imports B and B imports A
        pairs = []
        checked: set[tuple[str, str]] = set()
        for file_a, imports_a in import_map.items():
            module_a = file_a.replace("/", ".").replace(".py", "")
            for file_b, imports_b in import_map.items():
                if file_a == file_b:
                    continue
                key = tuple(sorted([file_a, file_b]))
                if key in checked:
                    continue
                checked.add(key)
                module_b = file_b.replace("/", ".").replace(".py", "")
                a_imports_b = any(module_b.endswith(imp) or imp.endswith(module_b.split(".")[-1]) for imp in imports_a)
                b_imports_a = any(module_a.endswith(imp) or imp.endswith(module_a.split(".")[-1]) for imp in imports_b)
                if a_imports_b and b_imports_a:
                    pairs.append((file_a, file_b))
        return pairs[:5]  # Cap at 5 for readability
