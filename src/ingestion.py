"""Codebase ingestion — builds a structured manifest of the target repo."""

from __future__ import annotations

import json
import os
import re
import fnmatch
from collections import Counter
from typing import Optional


SKIP_DIRS = {
    "node_modules", ".git", ".svn", "__pycache__", "venv", ".venv",
    "dist", "build", ".next", ".nuxt", ".output", "target",
    "Pods", ".gradle", "eggs", "*.egg-info",
}

FRAMEWORK_SIGNALS = {
    "next.js": ["next.config.js", "next.config.mjs", "next.config.ts"],
    "react": ["src/App.jsx", "src/App.tsx", "src/index.jsx", "src/index.tsx"],
    "vue": ["vue.config.js", "nuxt.config.js", "nuxt.config.ts"],
    "angular": ["angular.json"],
    "svelte": ["svelte.config.js"],
    "express": [],  # detected via package.json
    "fastapi": [],  # detected via requirements
    "django": ["manage.py"],
    "flask": [],    # detected via requirements
    "rails": ["Gemfile", "config/routes.rb"],
    "react-native": ["app.json", "metro.config.js"],
    "expo": ["app.json", "app.config.js", "app.config.ts"],
    "electron": [],  # detected via package.json
    "swift/ios": ["*.xcodeproj", "*.xcworkspace", "Package.swift"],
    "android/kotlin": ["build.gradle", "build.gradle.kts"],
}

DB_SIGNALS = {
    "supabase": ["@supabase/supabase-js", "supabase"],
    "firebase": ["firebase", "firebase-admin", "@firebase"],
    "prisma": ["@prisma/client", "prisma"],
    "drizzle": ["drizzle-orm"],
    "mongoose": ["mongoose"],
    "sqlalchemy": ["sqlalchemy", "SQLAlchemy"],
    "typeorm": ["typeorm"],
    "sequelize": ["sequelize"],
    "postgresql": ["pg", "psycopg2", "asyncpg"],
    "mysql": ["mysql2", "mysqlclient", "PyMySQL"],
    "sqlite": ["better-sqlite3", "sqlite3"],
    "mongodb": ["mongodb", "pymongo"],
    "redis": ["redis", "ioredis"],
}

AUTH_SIGNALS = {
    "supabase-auth": ["@supabase/auth-helpers", "supabase.auth", "createClient"],
    "firebase-auth": ["firebase/auth", "firebase-admin/auth"],
    "nextauth": ["next-auth", "@auth/core"],
    "clerk": ["@clerk/nextjs", "@clerk/clerk-js"],
    "auth0": ["@auth0/nextjs-auth0", "auth0"],
    "passport": ["passport"],
    "jwt-manual": ["jsonwebtoken", "jose", "PyJWT"],
}

DEPLOY_SIGNALS = {
    "vercel": ["vercel.json", ".vercel"],
    "netlify": ["netlify.toml", "_redirects"],
    "docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
    "aws": [".aws", "serverless.yml", "template.yaml", "cdk.json"],
    "gcp": ["app.yaml", ".gcloudignore"],
    "heroku": ["Procfile"],
    "railway": ["railway.json", "railway.toml"],
    "fly": ["fly.toml"],
    "render": ["render.yaml"],
}

CI_SIGNALS = {
    "github-actions": [".github/workflows"],
    "gitlab-ci": [".gitlab-ci.yml"],
    "circleci": [".circleci/config.yml"],
    "jenkins": ["Jenkinsfile"],
    "travis": [".travis.yml"],
}


def _walk_files(target_dir: str) -> list[str]:
    """Return all relative file paths, skipping common junk dirs."""
    result = []
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), target_dir).replace("\\", "/")
            result.append(rel)
    return result


def _detect_package_manager(target_dir: str) -> Optional[str]:
    for pm, lockfile in [("pnpm", "pnpm-lock.yaml"), ("yarn", "yarn.lock"),
                         ("bun", "bun.lockb"), ("npm", "package-lock.json"),
                         ("pip", "requirements.txt"), ("poetry", "poetry.lock"),
                         ("pipenv", "Pipfile.lock"), ("cargo", "Cargo.lock"),
                         ("go", "go.sum"), ("composer", "composer.lock")]:
        if os.path.exists(os.path.join(target_dir, lockfile)):
            return pm
    if os.path.exists(os.path.join(target_dir, "package.json")):
        return "npm"
    if os.path.exists(os.path.join(target_dir, "requirements.txt")):
        return "pip"
    return None


def _parse_package_json(target_dir: str) -> dict:
    path = os.path.join(target_dir, "package.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _parse_requirements_txt(target_dir: str) -> list[str]:
    path = os.path.join(target_dir, "requirements.txt")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        deps = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("-"):
                name = re.split(r"[>=<!\[]", line)[0].strip()
                if name:
                    deps.append(name)
        return deps
    except Exception:
        return []


def _detect_from_signals(signals: dict, all_files: list[str], all_deps: list[str]) -> list[str]:
    """Check signal dict against files and deps."""
    detected = []
    for name, indicators in signals.items():
        for indicator in indicators:
            # check if it's a dep name
            if any(indicator in d for d in all_deps):
                detected.append(name)
                break
            # check if it matches a file path
            for fp in all_files:
                if fnmatch.fnmatch(fp, indicator) or fp.endswith(indicator) or indicator in fp:
                    detected.append(name)
                    break
            else:
                continue
            break
    return detected


def _count_by_ext(files: list[str]) -> dict[str, int]:
    counter = Counter()
    for f in files:
        _, ext = os.path.splitext(f)
        if ext:
            counter[ext.lower()] += 1
    return dict(counter.most_common(20))


def _find_env_files(target_dir: str, all_files: list[str]) -> list[str]:
    return [f for f in all_files if os.path.basename(f).startswith(".env")]


def _find_env_var_refs(target_dir: str, all_files: list[str]) -> list[str]:
    """Find referenced env var names in source files."""
    env_vars = set()
    code_exts = {".js", ".jsx", ".ts", ".tsx", ".py", ".rb", ".go", ".rs"}
    for fp in all_files:
        _, ext = os.path.splitext(fp)
        if ext.lower() not in code_exts:
            continue
        full = os.path.join(target_dir, fp)
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            continue
        # process.env.VAR_NAME or os.environ / os.getenv
        env_vars.update(re.findall(r"process\.env\.([A-Z_][A-Z0-9_]*)", content))
        env_vars.update(re.findall(r'os\.(?:environ|getenv)\s*[\[\(]\s*["\']([A-Z_][A-Z0-9_]*)', content))
    return sorted(env_vars)


def _detect_frameworks(all_files: list[str], all_deps: list[str]) -> list[str]:
    detected = []
    # file-based detection
    for fw, indicators in FRAMEWORK_SIGNALS.items():
        for indicator in indicators:
            for fp in all_files:
                if fnmatch.fnmatch(fp, indicator) or fp == indicator:
                    if fw not in detected:
                        detected.append(fw)
                    break

    # dep-based detection for frameworks without file signals
    dep_str = " ".join(all_deps).lower()
    dep_checks = [
        ("next.js", ["next"]),
        ("react", ["react"]),
        ("vue", ["vue"]),
        ("angular", ["@angular/core"]),
        ("svelte", ["svelte"]),
        ("express", ["express"]),
        ("fastapi", ["fastapi"]),
        ("flask", ["flask"]),
        ("django", ["django"]),
        ("react-native", ["react-native"]),
        ("expo", ["expo"]),
        ("electron", ["electron"]),
    ]
    for fw, deps in dep_checks:
        if fw not in detected and any(d.lower() in dep_str for d in deps):
            detected.append(fw)
    return detected


def _check_gitignore(target_dir: str) -> dict:
    path = os.path.join(target_dir, ".gitignore")
    if not os.path.isfile(path):
        return {"exists": False, "entries": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            entries = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        return {"exists": True, "entries": entries}
    except Exception:
        return {"exists": False, "entries": []}


def _detect_language(files_by_ext: dict) -> str:
    lang_map = {
        ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript",
        ".py": "python",
        ".rb": "ruby",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".kt": "kotlin",
        ".swift": "swift",
        ".cs": "csharp",
        ".php": "php",
    }
    scored: Counter = Counter()
    for ext, count in files_by_ext.items():
        lang = lang_map.get(ext)
        if lang:
            scored[lang] += count
    if not scored:
        return "unknown"
    return scored.most_common(1)[0][0]


def _detect_tsconfig(target_dir: str) -> Optional[dict]:
    path = os.path.join(target_dir, "tsconfig.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # strip comments (basic)
        content = re.sub(r"//.*", "", content)
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        data = json.loads(content)
        co = data.get("compilerOptions", {})
        return {
            "strict": co.get("strict", False),
            "noImplicitAny": co.get("noImplicitAny", False),
            "strictNullChecks": co.get("strictNullChecks", False),
        }
    except Exception:
        return None


def build_manifest(target_dir: str) -> dict:
    """Build and return the codebase manifest for the target directory."""
    target_dir = os.path.abspath(target_dir)
    all_files = _walk_files(target_dir)

    pkg = _parse_package_json(target_dir)
    all_deps_node = list((pkg.get("dependencies", {}) | pkg.get("devDependencies", {})).keys()) if pkg else []
    all_deps_python = _parse_requirements_txt(target_dir)
    all_deps = all_deps_node + all_deps_python

    files_by_ext = _count_by_ext(all_files)
    env_files = _find_env_files(target_dir, all_files)
    env_vars = _find_env_var_refs(target_dir, all_files)

    frameworks = _detect_frameworks(all_files, all_deps)
    databases = _detect_from_signals(DB_SIGNALS, all_files, all_deps)
    auth = _detect_from_signals(AUTH_SIGNALS, all_files, all_deps)
    deployment = _detect_from_signals(DEPLOY_SIGNALS, all_files, all_deps)
    ci_cd = _detect_from_signals(CI_SIGNALS, all_files, all_deps)

    test_patterns = ["*.test.*", "*.spec.*", "*_test.*", "*_spec.*", "test_*", "tests/*", "__tests__/*"]
    test_files = []
    for fp in all_files:
        base = os.path.basename(fp)
        for pat in test_patterns:
            if fnmatch.fnmatch(base, pat) or fnmatch.fnmatch(fp, pat):
                test_files.append(fp)
                break

    manifest = {
        "target_dir": target_dir,
        "file_count": len(all_files),
        "files_by_extension": files_by_ext,
        "primary_language": _detect_language(files_by_ext),
        "package_manager": _detect_package_manager(target_dir),
        "frameworks": frameworks,
        "databases": databases,
        "auth": auth,
        "deployment": deployment,
        "ci_cd": ci_cd,
        "dependencies": {
            "node": all_deps_node,
            "python": all_deps_python,
            "total_count": len(all_deps),
        },
        "env_files": env_files,
        "env_vars_referenced": env_vars,
        "gitignore": _check_gitignore(target_dir),
        "tsconfig": _detect_tsconfig(target_dir),
        "test_files": test_files,
        "test_file_count": len(test_files),
        "has_dockerfile": any(f.lower() in ("dockerfile", "docker-compose.yml", "docker-compose.yaml") or "Dockerfile" in f for f in all_files),
        "has_readme": any(os.path.basename(f).lower().startswith("readme") for f in all_files),
    }
    return manifest


def save_manifest(manifest: dict, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "manifest.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return path
