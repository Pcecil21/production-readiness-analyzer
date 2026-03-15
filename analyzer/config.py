"""Configuration loading for .readiness.yml files."""

from pathlib import Path

import yaml


DEFAULT_CONFIG = {
    "exclude": ["node_modules/", "vendor/", ".git/", "__pycache__/", ".venv/", "venv/"],
    "thresholds": {
        "overall": 0,
        "security": 0,
        "reliability": 0,
        "observability": 0,
        "testing": 0,
        "documentation": 0,
        "operations": 0,
    },
    "disabled_checks": [],
}


def load_config(path: str | Path) -> dict:
    """Load and merge user config with defaults."""
    cfg = dict(DEFAULT_CONFIG)
    path = Path(path)
    if path.is_file():
        with open(path) as f:
            user_cfg = yaml.safe_load(f) or {}
        if "exclude" in user_cfg:
            cfg["exclude"] = list(set(cfg["exclude"] + user_cfg["exclude"]))
        if "thresholds" in user_cfg:
            cfg["thresholds"].update(user_cfg["thresholds"])
        if "disabled_checks" in user_cfg:
            cfg["disabled_checks"] = user_cfg["disabled_checks"]
    return cfg
