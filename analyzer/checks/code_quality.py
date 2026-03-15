"""Code quality checks — inspired by simplify & review skills.

Detects complexity hotspots, code duplication signals, oversized files,
SQL safety issues, and structural anti-patterns.
"""

import re
from pathlib import Path

from analyzer.checks import BaseChecker
from analyzer.models import CategoryResult, Finding, Severity

SOURCE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php", ".cs", ".kt", ".swift"}
MAX_FILE_LINES = 500
MAX_FUNCTION_LINES = 80


class CodeQualityChecker(BaseChecker):
    def run(self) -> CategoryResult:
        findings: list[Finding] = []
        score = 100

        source_files = [f for f in self.files if f.suffix in SOURCE_EXTS]

        # CQ-001: Oversized files
        for f in source_files:
            content = self._read_safe(f)
            line_count = content.count("\n")
            if line_count > MAX_FILE_LINES:
                findings.append(Finding(
                    check_id="CQ-001",
                    category="code_quality",
                    severity=Severity.WARNING,
                    message=f"{self._rel(f)} has {line_count} lines (>{MAX_FILE_LINES}) — consider splitting",
                    file=self._rel(f),
                ))
                score -= 3

        # CQ-002: Long functions/methods
        for f in source_files:
            content = self._read_safe(f)
            long_fns = self._find_long_functions(content, f)
            for name, line_num, length in long_fns:
                findings.append(Finding(
                    check_id="CQ-002",
                    category="code_quality",
                    severity=Severity.WARNING,
                    message=f"Function '{name}' in {self._rel(f)}:{line_num} is {length} lines (>{MAX_FUNCTION_LINES})",
                    file=self._rel(f),
                    line=line_num,
                ))
                score -= 3

        # CQ-003: TODO/FIXME/HACK/XXX markers
        todo_count = 0
        for f in source_files:
            content = self._read_safe(f)
            matches = re.findall(r'\b(TODO|FIXME|HACK|XXX)\b', content)
            todo_count += len(matches)
        if todo_count > 10:
            findings.append(Finding(
                check_id="CQ-003",
                category="code_quality",
                severity=Severity.WARNING,
                message=f"{todo_count} TODO/FIXME/HACK markers found — unresolved tech debt",
            ))
            score -= 5
        elif todo_count > 0:
            findings.append(Finding(
                check_id="CQ-003",
                category="code_quality",
                severity=Severity.INFO,
                message=f"{todo_count} TODO/FIXME/HACK marker(s) found",
            ))

        # CQ-004: Raw SQL without parameterization
        all_content = self._aggregate(source_files)
        sql_concat = re.findall(
            r'(?:execute|query|raw)\s*\([^)]*(?:\+|f"|f\'|%s|\.format\()',
            all_content, re.IGNORECASE,
        )
        if sql_concat:
            findings.append(Finding(
                check_id="CQ-004",
                category="code_quality",
                severity=Severity.CRITICAL,
                message=f"Possible SQL injection: {len(sql_concat)} raw SQL string concatenation(s) detected",
            ))
            score -= 15

        # CQ-005: console.log / print debugging left in
        debug_patterns = [
            (r'console\.log\(', ".js/.ts"),
            (r'\bprint\s*\(.*debug', ".py"),
            (r'System\.out\.print', ".java"),
            (r'fmt\.Print', ".go"),
        ]
        debug_count = 0
        for pattern, _ in debug_patterns:
            debug_count += len(re.findall(pattern, all_content, re.IGNORECASE))
        if debug_count > 5:
            findings.append(Finding(
                check_id="CQ-005",
                category="code_quality",
                severity=Severity.INFO,
                message=f"{debug_count} debug print/log statements found — consider removing before production",
            ))
            score -= 3

        # CQ-006: Deeply nested code (4+ levels)
        deep_nesting_count = 0
        for f in source_files:
            content = self._read_safe(f)
            for i, line in enumerate(content.splitlines(), 1):
                indent = len(line) - len(line.lstrip())
                # 4 levels ≈ 16 spaces or 4 tabs
                if indent >= 16 or line.count("\t") >= 4:
                    deep_nesting_count += 1
        if deep_nesting_count > 20:
            findings.append(Finding(
                check_id="CQ-006",
                category="code_quality",
                severity=Severity.WARNING,
                message=f"{deep_nesting_count} lines with deep nesting (4+ levels) — extract functions to reduce complexity",
            ))
            score -= 5

        # CQ-007: Duplicated code signals (identical long lines)
        line_freq: dict[str, int] = {}
        for f in source_files:
            content = self._read_safe(f)
            for line in content.splitlines():
                stripped = line.strip()
                if len(stripped) > 40 and not stripped.startswith(("#", "//", "/*", "*", "import", "from")):
                    line_freq[stripped] = line_freq.get(stripped, 0) + 1
        duplicates = sum(1 for count in line_freq.values() if count >= 3)
        if duplicates > 5:
            findings.append(Finding(
                check_id="CQ-007",
                category="code_quality",
                severity=Severity.WARNING,
                message=f"{duplicates} code lines appear 3+ times — likely duplication to refactor",
            ))
            score -= 5

        return CategoryResult(name="code_quality", score=max(0, score), findings=findings)

    def _find_long_functions(self, content: str, path: Path) -> list[tuple[str, int, int]]:
        """Find functions exceeding MAX_FUNCTION_LINES."""
        results = []
        if path.suffix in (".py",):
            pattern = r'^(def|async def)\s+(\w+)'
        elif path.suffix in (".js", ".ts", ".jsx", ".tsx"):
            pattern = r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\())'
        elif path.suffix in (".go",):
            pattern = r'^func\s+(?:\([^)]+\)\s+)?(\w+)'
        elif path.suffix in (".java", ".cs", ".kt"):
            pattern = r'(?:public|private|protected|static|\s)+\w+\s+(\w+)\s*\('
        else:
            return results

        lines = content.splitlines()
        func_starts: list[tuple[str, int]] = []
        for i, line in enumerate(lines):
            m = re.match(pattern, line)
            if m:
                name = next((g for g in m.groups() if g), "unknown")
                func_starts.append((name, i + 1))

        for idx, (name, start) in enumerate(func_starts):
            end = func_starts[idx + 1][1] - 1 if idx + 1 < len(func_starts) else len(lines)
            length = end - start + 1
            if length > MAX_FUNCTION_LINES:
                results.append((name, start, length))
        return results

    def _aggregate(self, files: list[Path]) -> str:
        return "\n".join(self._read_safe(f, max_bytes=100_000) for f in files)
