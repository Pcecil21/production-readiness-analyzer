"""Accessibility & UI quality checks — inspired by browse, gstack, qa skills.

Scans for WCAG compliance signals, responsive design patterns, form accessibility,
and browser testing infrastructure.
"""

import re

from analyzer.checks import BaseChecker
from analyzer.models import CategoryResult, Finding, Severity

HTML_LIKE_EXTS = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".erb", ".hbs", ".ejs", ".blade.php"}
STYLE_EXTS = {".css", ".scss", ".sass", ".less", ".styl"}


class AccessibilityChecker(BaseChecker):
    def run(self) -> CategoryResult:
        findings: list[Finding] = []
        score = 100

        html_files = [f for f in self.files if f.suffix in HTML_LIKE_EXTS]
        style_files = [f for f in self.files if f.suffix in STYLE_EXTS]
        all_html = self._aggregate(html_files)
        all_styles = self._aggregate(style_files)

        # Skip if no frontend files
        if not html_files and not style_files:
            return CategoryResult(name="accessibility", score=100, findings=[
                Finding(
                    check_id="A11Y-000",
                    category="accessibility",
                    severity=Severity.INFO,
                    message="No frontend files detected — accessibility checks skipped",
                ),
            ])

        # A11Y-001: Images without alt text
        img_tags = re.findall(r'<img\b[^>]*>', all_html, re.IGNORECASE)
        imgs_without_alt = [t for t in img_tags if 'alt=' not in t.lower()]
        if imgs_without_alt:
            findings.append(Finding(
                check_id="A11Y-001",
                category="accessibility",
                severity=Severity.CRITICAL,
                message=f"{len(imgs_without_alt)} <img> tag(s) without alt attribute — screen readers can't describe these",
            ))
            score -= 15

        # A11Y-002: Form inputs without labels
        # JSX inputs span multiple lines and may contain > in expressions,
        # so we grab up to 500 chars after <input to catch all attributes.
        inputs_without_label = []
        for m in re.finditer(r'<input\b', all_html, re.IGNORECASE):
            chunk = all_html[m.start():m.start() + 500].lower()
            if 'aria-label' in chunk or 'id=' in chunk:
                continue
            if 'type="hidden"' in chunk or 'type="submit"' in chunk:
                continue
            inputs_without_label.append(chunk[:80])
        if inputs_without_label:
            findings.append(Finding(
                check_id="A11Y-002",
                category="accessibility",
                severity=Severity.WARNING,
                message=f"{len(inputs_without_label)} <input> element(s) may lack associated labels",
            ))
            score -= 10

        # A11Y-003: ARIA landmarks and roles
        aria_patterns = [r'role=', r'aria-', r'<main', r'<nav', r'<header', r'<footer', r'<aside']
        has_aria = any(re.search(p, all_html, re.IGNORECASE) for p in aria_patterns)
        if html_files and not has_aria:
            findings.append(Finding(
                check_id="A11Y-003",
                category="accessibility",
                severity=Severity.WARNING,
                message="No ARIA roles or semantic landmarks found — assistive technology navigation will be poor",
            ))
            score -= 10

        # A11Y-004: Color contrast / focus indicators in CSS
        focus_patterns = [r':focus', r':focus-visible', r'outline:', r'focus-ring']
        has_focus = any(re.search(p, all_styles) for p in focus_patterns)
        if style_files and not has_focus:
            findings.append(Finding(
                check_id="A11Y-004",
                category="accessibility",
                severity=Severity.WARNING,
                message="No :focus or :focus-visible styles found — keyboard navigation will be invisible",
            ))
            score -= 10

        # A11Y-005: Responsive design (media queries or responsive framework)
        responsive_patterns = [r'@media', r'responsive', r'tailwind', r'bootstrap', r'flex', r'grid']
        has_responsive = any(re.search(p, all_styles, re.IGNORECASE) for p in responsive_patterns)
        if style_files and not has_responsive:
            findings.append(Finding(
                check_id="A11Y-005",
                category="accessibility",
                severity=Severity.WARNING,
                message="No responsive design patterns (media queries, flex/grid) detected",
            ))
            score -= 10

        # A11Y-006: Accessibility testing tools
        a11y_tools = [
            "axe", "pa11y", "lighthouse", "jest-axe", "cypress-axe",
            "testing-library", "a11y", "accessib", "wcag",
        ]
        all_file_content = self._aggregate(self.files[:200])  # scan configs too
        has_a11y_tooling = any(re.search(t, all_file_content, re.IGNORECASE) for t in a11y_tools)
        if not has_a11y_tooling:
            findings.append(Finding(
                check_id="A11Y-006",
                category="accessibility",
                severity=Severity.INFO,
                message="No accessibility testing tools (axe, pa11y, lighthouse) detected",
            ))
            score -= 5

        # A11Y-007: Skip navigation link
        has_skip = re.search(r'skip.*nav|skip.*content|skiplink', all_html, re.IGNORECASE)
        if html_files and not has_skip:
            findings.append(Finding(
                check_id="A11Y-007",
                category="accessibility",
                severity=Severity.INFO,
                message="No 'skip to content' link found — keyboard users must tab through full nav each page",
            ))
            score -= 3

        # A11Y-008: Language attribute on HTML
        has_lang = re.search(r'<html[^>]*\slang=', all_html, re.IGNORECASE)
        html_root_files = [f for f in self.files if f.suffix in (".html", ".htm")]
        if html_root_files and not has_lang:
            findings.append(Finding(
                check_id="A11Y-008",
                category="accessibility",
                severity=Severity.WARNING,
                message="No lang attribute on <html> — screen readers can't determine the page language",
            ))
            score -= 5

        return CategoryResult(name="accessibility", score=max(0, score), findings=findings)

    def _aggregate(self, files: list) -> str:
        parts = []
        for f in files:
            parts.append(self._read_safe(f, max_bytes=100_000))
        return "\n".join(parts)
