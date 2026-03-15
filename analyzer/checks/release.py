"""Release & shipping readiness checks — inspired by ship & retro skills.

Validates versioning, changelog hygiene, branch strategy, release automation,
and commit quality.
"""

import re

from analyzer.checks import BaseChecker
from analyzer.models import CategoryResult, Finding, Severity


class ReleaseChecker(BaseChecker):
    def run(self) -> CategoryResult:
        findings: list[Finding] = []
        score = 100

        # REL-S01: Version declaration exists
        version_found = False
        version_files = [
            ("package.json", r'"version"\s*:\s*"'),
            ("pyproject.toml", r'version\s*=\s*"'),
            ("Cargo.toml", r'version\s*=\s*"'),
            ("build.gradle", r'version\s*='),
            ("VERSION", r'.+'),
            ("version.txt", r'.+'),
        ]
        for fname, pattern in version_files:
            for f in self.files:
                if f.name == fname:
                    content = self._read_safe(f)
                    if re.search(pattern, content):
                        version_found = True
                        break
        # Also check for __version__ in Python
        for f in self.files:
            if f.name == "__init__.py":
                content = self._read_safe(f)
                if "__version__" in content:
                    version_found = True
                    break
        if not version_found:
            findings.append(Finding(
                check_id="SHP-001",
                category="release",
                severity=Severity.WARNING,
                message="No version declaration found — releases won't be traceable",
            ))
            score -= 15

        # REL-S02: CHANGELOG exists and is maintained
        changelog_files = [f for f in self.files if f.name.lower() in (
            "changelog.md", "changelog", "changes.md", "history.md", "releases.md",
        )]
        if not changelog_files:
            findings.append(Finding(
                check_id="SHP-002",
                category="release",
                severity=Severity.WARNING,
                message="No CHANGELOG — users and developers can't track what changed between releases",
            ))
            score -= 10
        else:
            content = self._read_safe(changelog_files[0])
            # Check for "Unreleased" section — a sign of active maintenance
            if "unreleased" not in content.lower() and len(content) < 100:
                findings.append(Finding(
                    check_id="SHP-002",
                    category="release",
                    severity=Severity.INFO,
                    message="CHANGELOG exists but appears sparse — keep it updated with each release",
                ))
                score -= 3

        # REL-S03: Release automation (GitHub Actions release, semantic-release, etc.)
        release_patterns = [
            r'release', r'publish', r'deploy', r'semantic-release',
            r'goreleaser', r'changesets', r'np\b', r'bump2version',
        ]
        ci_files = [f for f in self.files if ".github/workflows" in str(f).replace("\\", "/") or f.name in (
            ".releaserc", ".goreleaser.yml", ".changeset", "release.config.js",
        )]
        has_release_automation = False
        for f in ci_files:
            content = self._read_safe(f)
            if any(re.search(p, content, re.IGNORECASE) for p in release_patterns):
                has_release_automation = True
                break
        if not has_release_automation:
            findings.append(Finding(
                check_id="SHP-003",
                category="release",
                severity=Severity.INFO,
                message="No automated release pipeline detected — manual releases are error-prone",
            ))
            score -= 10

        # REL-S04: Git tags / release conventions
        # Check for any tag references or release configuration
        has_tag_config = any(
            f.name in (".releaserc", ".goreleaser.yml", "release.config.js", ".changeset")
            for f in self.files
        )
        if not has_tag_config and not has_release_automation:
            findings.append(Finding(
                check_id="SHP-004",
                category="release",
                severity=Severity.INFO,
                message="No release/tag configuration — consider semantic versioning with automated tags",
            ))
            score -= 5

        # REL-S05: Lockfile freshness check — ensure lockfiles exist alongside manifests
        manifest_lock_pairs = [
            ("package.json", ["package-lock.json", "yarn.lock", "pnpm-lock.yaml"]),
            ("Gemfile", ["Gemfile.lock"]),
            ("Cargo.toml", ["Cargo.lock"]),
            ("go.mod", ["go.sum"]),
            ("composer.json", ["composer.lock"]),
        ]
        file_names = {f.name for f in self.files}
        for manifest, locks in manifest_lock_pairs:
            if manifest in file_names:
                if not any(lock in file_names for lock in locks):
                    findings.append(Finding(
                        check_id="SHP-005",
                        category="release",
                        severity=Severity.WARNING,
                        message=f"{manifest} found without a lockfile — builds are non-reproducible",
                    ))
                    score -= 10
                    break

        # REL-S06: Branch protection indicators
        codeowners = any(f.name == "CODEOWNERS" for f in self.files)
        branch_protection = any("branch-protection" in f.name.lower() or "ruleset" in f.name.lower() for f in self.files)
        if not codeowners and not branch_protection:
            findings.append(Finding(
                check_id="SHP-006",
                category="release",
                severity=Severity.INFO,
                message="No CODEOWNERS file — consider adding for automated review assignment",
            ))
            score -= 5

        return CategoryResult(name="release", score=max(0, score), findings=findings)
