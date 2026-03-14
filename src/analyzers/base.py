"""Base analyzer interface. Every analyzer produces structured findings."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Finding:
    id: str
    severity: str          # critical | high | medium | low | info
    category: str
    title: str
    file: Optional[str] = None
    line: Optional[int] = None
    description: str = ""
    why_it_matters: str = ""
    recommendation: str = ""
    effort_hours: float = 0
    depends_on: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class BaseAnalyzer:
    """Base class for all production-readiness analyzers."""

    name: str = "base"
    description: str = ""

    def __init__(self, target_dir: str, manifest: dict, context: dict):
        self.target_dir = target_dir
        self.manifest = manifest
        self.context = context
        self.findings: list[Finding] = []
        self._finding_counter = 0

    def _next_id(self, prefix: str) -> str:
        self._finding_counter += 1
        return f"{prefix}-{self._finding_counter:03d}"

    def _read_file(self, rel_path: str) -> Optional[str]:
        full = os.path.join(self.target_dir, rel_path)
        if not os.path.isfile(full):
            return None
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None

    def _find_files(self, *patterns: str) -> list[str]:
        """Walk target_dir and return relative paths matching any glob pattern."""
        import fnmatch
        matched = []
        for root, _dirs, files in os.walk(self.target_dir):
            # skip hidden dirs / node_modules / venv
            rel_root = os.path.relpath(root, self.target_dir)
            if any(part.startswith(".") or part in ("node_modules", "venv", ".venv", "__pycache__", "dist", "build")
                   for part in rel_root.split(os.sep)):
                continue
            for fname in files:
                rel = os.path.relpath(os.path.join(root, fname), self.target_dir)
                rel = rel.replace("\\", "/")
                for pat in patterns:
                    if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(fname, pat):
                        matched.append(rel)
                        break
        return matched

    def _add(self, **kwargs) -> Finding:
        f = Finding(**kwargs)
        self.findings.append(f)
        return f

    def run(self) -> list[Finding]:
        """Override in subclasses. Run analysis and populate self.findings."""
        raise NotImplementedError

    def save(self, output_dir: str) -> str:
        """Write findings to JSON file, return the path."""
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{self.name}.json")
        data = {
            "analyzer": self.name,
            "description": self.description,
            "finding_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return path
