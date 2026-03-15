"""Base checker interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from analyzer.models import CategoryResult


class BaseChecker(ABC):
    """Base class for all category checkers."""

    def __init__(self, target: Path, files: list[Path], config: dict):
        self.target = target
        self.files = files
        self.config = config

    @abstractmethod
    def run(self) -> CategoryResult:
        ...

    def _rel(self, path: Path) -> str:
        return str(path.relative_to(self.target)).replace("\\", "/")

    def _has_file(self, *patterns: str) -> bool:
        """Check if any file matches the given name patterns (case-insensitive)."""
        for f in self.files:
            name_lower = f.name.lower()
            for pat in patterns:
                if name_lower == pat.lower() or f.name.endswith(pat):
                    return True
        return False

    def _find_files(self, *extensions: str) -> list[Path]:
        """Return files matching any of the given extensions."""
        return [f for f in self.files if any(f.name.endswith(ext) for ext in extensions)]

    def _read_safe(self, path: Path, max_bytes: int = 512_000) -> str:
        """Read file content, returning empty string on failure."""
        try:
            return path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
        except Exception:
            return ""
