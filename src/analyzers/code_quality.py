"""Code quality analyzer — structure, types, errors, deps, dead code."""

from __future__ import annotations
import os
import re
from collections import Counter
from .base import BaseAnalyzer

CODE_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".py", ".rb", ".go", ".rs", ".java", ".kt", ".swift", ".php"}


class CodeQualityAnalyzer(BaseAnalyzer):
    name = "code_quality"
    description = "File structure, type safety, error handling, dependency health, dead code, TODOs"

    def run(self) -> list:
        self._check_file_sizes()
        self._check_typescript_strictness()
        self._check_any_usage()
        self._check_error_handling()
        self._check_dependency_count()
        self._check_todos_and_hacks()
        self._check_code_organization()
        self._check_unused_dependencies()
        self._check_console_statements()
        return self.findings

    def _check_file_sizes(self):
        large_files = []
        code_files = [f for f in self._find_files("*") if os.path.splitext(f)[1].lower() in CODE_EXTENSIONS]
        for fp in code_files:
            content = self._read_file(fp)
            if not content:
                continue
            lines = len(content.splitlines())
            if lines > 500:
                large_files.append((fp, lines))

        large_files.sort(key=lambda x: x[1], reverse=True)
        if large_files:
            top = large_files[:5]
            desc = "\n".join(f"  - {fp}: {lines} lines" for fp, lines in top)
            self._add(
                id=self._next_id("CQ"),
                severity="medium",
                category="file_size",
                title=f"{len(large_files)} files exceed 500 lines",
                file=top[0][0],
                line=1,
                description=f"Largest files:\n{desc}",
                why_it_matters="Large files are hard to navigate, test, and review. They often indicate mixed responsibilities that should be separated.",
                recommendation="Break large files into focused modules. Extract utility functions, separate UI components from business logic.",
                effort_hours=len(large_files) * 2,
            )

    def _check_typescript_strictness(self):
        tsconfig = self.manifest.get("tsconfig")
        if tsconfig is None:
            # Not a TypeScript project
            lang = self.manifest.get("primary_language", "")
            if lang == "javascript":
                js_files = self._find_files("*.js", "*.jsx")
                if len(js_files) > 10:
                    self._add(
                        id=self._next_id("CQ"),
                        severity="medium",
                        category="type_safety",
                        title="JavaScript project without TypeScript",
                        description=f"Project has {len(js_files)} JavaScript files but no tsconfig.json.",
                        why_it_matters="TypeScript catches entire categories of bugs at compile time. Migrating later is harder the larger the codebase grows.",
                        recommendation="Consider migrating to TypeScript incrementally. Start with 'allowJs: true' and rename files one at a time.",
                        effort_hours=len(js_files) * 0.5,
                    )
            return

        if not tsconfig.get("strict"):
            self._add(
                id=self._next_id("CQ"),
                severity="medium",
                category="type_safety",
                title="TypeScript strict mode is disabled",
                description=f"tsconfig.json has strict: {tsconfig.get('strict', 'not set')}.",
                why_it_matters="Without strict mode, TypeScript misses null checks, implicit any types, and other common sources of runtime errors.",
                recommendation="Enable 'strict: true' in tsconfig.json. Fix resulting type errors — they're almost always real bugs.",
                effort_hours=4,
            )

    def _check_any_usage(self):
        if self.manifest.get("primary_language") != "typescript":
            return

        ts_files = self._find_files("*.ts", "*.tsx")
        any_count = 0
        worst_file = None
        worst_count = 0

        for fp in ts_files:
            content = self._read_file(fp)
            if not content:
                continue
            # Match `: any`, `as any`, `<any>` but not in comments
            matches = re.findall(r'(?::\s*any\b|as\s+any\b|<any>)', content)
            file_count = len(matches)
            any_count += file_count
            if file_count > worst_count:
                worst_count = file_count
                worst_file = fp

        if any_count > 5:
            self._add(
                id=self._next_id("CQ"),
                severity="medium",
                category="type_safety",
                title=f"Excessive 'any' type usage ({any_count} occurrences)",
                file=worst_file,
                description=f"Found {any_count} uses of 'any' across {len(ts_files)} TypeScript files.",
                why_it_matters="Each 'any' is an escape hatch that disables type checking. It defeats the purpose of using TypeScript.",
                recommendation="Replace 'any' with proper types. Use 'unknown' when the type is truly dynamic, then narrow with type guards.",
                effort_hours=any_count * 0.25,
            )

    def _check_error_handling(self):
        code_files = [f for f in self._find_files("*") if os.path.splitext(f)[1].lower() in CODE_EXTENSIONS]
        empty_catch_files = []

        for fp in code_files[:30]:
            content = self._read_file(fp)
            if not content:
                continue
            # Empty catch blocks or catch that only has a comment
            if re.search(r'catch\s*\([^)]*\)\s*\{\s*(?://[^\n]*)?\s*\}', content):
                empty_catch_files.append(fp)
            # Swallowed errors (catch with no logging/rethrowing)
            if re.search(r'\.catch\(\s*\(\s*\)\s*=>\s*\{\s*\}\s*\)', content):
                empty_catch_files.append(fp)

        if empty_catch_files:
            unique = list(set(empty_catch_files))
            self._add(
                id=self._next_id("CQ"),
                severity="high",
                category="error_handling",
                title=f"Empty catch blocks found in {len(unique)} files",
                file=unique[0],
                description=f"Files with swallowed errors: {', '.join(unique[:5])}",
                why_it_matters="Swallowed errors hide bugs. Your app fails silently, users see broken behavior, and you have no idea why because the error was discarded.",
                recommendation="At minimum, log the error. Better: handle it specifically or re-throw. Never ignore errors.",
                effort_hours=len(unique) * 0.5,
            )

    def _check_dependency_count(self):
        deps = self.manifest.get("dependencies", {})
        node_deps = deps.get("node", [])
        total = deps.get("total_count", 0)

        if total > 50:
            self._add(
                id=self._next_id("CQ"),
                severity="low",
                category="dependencies",
                title=f"High dependency count ({total} packages)",
                description=f"Project has {total} dependencies. Large dependency trees increase attack surface, install time, and bundle size.",
                why_it_matters="Each dependency is code you don't control. More deps = more security risk, more breakage from updates, slower installs.",
                recommendation="Audit dependencies: remove unused ones, replace heavy libraries with lighter alternatives (e.g., date-fns instead of moment).",
                effort_hours=3,
            )

    def _check_todos_and_hacks(self):
        code_files = [f for f in self._find_files("*") if os.path.splitext(f)[1].lower() in CODE_EXTENSIONS]
        todos = []
        hacks = []

        for fp in code_files:
            content = self._read_file(fp)
            if not content:
                continue
            for line_num, line in enumerate(content.splitlines(), 1):
                if re.search(r'\bTODO\b', line):
                    todos.append((fp, line_num, line.strip()[:80]))
                if re.search(r'\b(?:HACK|FIXME|XXX|WORKAROUND)\b', line):
                    hacks.append((fp, line_num, line.strip()[:80]))

        if hacks:
            desc_lines = "\n".join(f"  - {fp}:{ln}: {text}" for fp, ln, text in hacks[:10])
            self._add(
                id=self._next_id("CQ"),
                severity="high",
                category="code_debt",
                title=f"{len(hacks)} HACK/FIXME/WORKAROUND markers found",
                file=hacks[0][0],
                line=hacks[0][1],
                description=f"These are self-documented problems:\n{desc_lines}",
                why_it_matters="The original author flagged these as known issues. They're likely the highest-value fixes because someone already identified the problem.",
                recommendation="Review each HACK/FIXME. Fix or convert to tracked issues before production.",
                effort_hours=len(hacks) * 1,
            )

        if len(todos) > 10:
            self._add(
                id=self._next_id("CQ"),
                severity="low",
                category="code_debt",
                title=f"{len(todos)} TODO comments found",
                description=f"Large number of TODOs suggests incomplete features or deferred decisions.",
                why_it_matters="TODOs in production code are promises to your future self. Too many means features shipped incomplete.",
                recommendation="Review TODOs: convert important ones to issues, delete stale ones, finish critical ones before launch.",
                effort_hours=len(todos) * 0.25,
            )

    def _check_code_organization(self):
        all_files = [f for f in self._find_files("*") if os.path.splitext(f)[1].lower() in CODE_EXTENSIONS]
        if not all_files:
            return

        # Check for all code in root directory (no structure)
        root_code_files = [f for f in all_files if "/" not in f]
        if len(root_code_files) > 10:
            self._add(
                id=self._next_id("CQ"),
                severity="medium",
                category="organization",
                title=f"{len(root_code_files)} code files in project root",
                description="Most code lives in the root directory rather than organized subdirectories.",
                why_it_matters="Flat file structures become unnavigable as the project grows. It's harder to find things, harder to enforce boundaries.",
                recommendation="Organize into directories by concern: src/components, src/lib, src/api, src/utils, etc.",
                effort_hours=4,
            )

    def _check_unused_dependencies(self):
        deps = self.manifest.get("dependencies", {})
        node_deps = deps.get("node", [])
        if not node_deps:
            return

        # Simple heuristic: check if dependency name appears in any source file
        code_files = self._find_files("*.ts", "*.tsx", "*.js", "*.jsx")
        all_code = ""
        for fp in code_files[:50]:
            content = self._read_file(fp)
            if content:
                all_code += content

        possibly_unused = []
        for dep in node_deps:
            # Skip types packages and common implicit deps
            if dep.startswith("@types/") or dep in ("typescript", "eslint", "prettier",
                                                      "tailwindcss", "postcss", "autoprefixer"):
                continue
            # Check if the dep name appears in import/require statements
            if dep not in all_code:
                possibly_unused.append(dep)

        if len(possibly_unused) > 3:
            self._add(
                id=self._next_id("CQ"),
                severity="low",
                category="dependencies",
                title=f"{len(possibly_unused)} possibly unused dependencies",
                description=f"These deps are in package.json but not found in source: {', '.join(possibly_unused[:10])}",
                why_it_matters="Unused dependencies increase install time, bundle size, and attack surface for no benefit.",
                recommendation="Verify each with 'npx depcheck' and remove truly unused ones.",
                effort_hours=1,
            )

    def _check_console_statements(self):
        code_files = self._find_files("*.ts", "*.tsx", "*.js", "*.jsx")
        console_count = 0
        for fp in code_files[:30]:
            content = self._read_file(fp)
            if content:
                console_count += len(re.findall(r'console\.(log|debug|info|warn|error)\(', content))

        if console_count > 20:
            self._add(
                id=self._next_id("CQ"),
                severity="low",
                category="code_cleanup",
                title=f"{console_count}+ console statements in source code",
                description="Heavy use of console.log suggests debugging code left in the codebase.",
                why_it_matters="Console statements clutter browser dev tools for users and can leak implementation details.",
                recommendation="Remove debug console.logs. Keep intentional console.error/warn for actual error conditions. Use a logger for server-side code.",
                effort_hours=2,
            )
