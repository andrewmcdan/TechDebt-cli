from __future__ import annotations
import os, yaml
from dataclasses import dataclass, field
from typing import Any, Dict

DEFAULT_CONFIG = {
    "weights": {
        "inline_priority": 1.0,
        "age_days": 0.6,
        "churn": 0.6,
        "complexity": 0.7,
        "deps_outdated": 0.8,
        "no_tests": 0.8,
        "lint_suppress": 0.5,
        "deprecated": 0.7,
    },
    "markers": [
        {
            "pattern": r"(TODO|FIXME|HACK|XXX|BUG|OPTIMIZE)",
            "priority_from": r"\\[(P\\d)\\]",
            "owner_from": r"@([a-z0-9_-]+)",
        }
    ],
    "tests": {
        "convention": {
            "src_globs": ["src/**/*.ts", "app/**/*.py"],
            "test_globs": ["**/*.test.ts", "tests/**/*.py"],
        }
    },
    "dependencies": {
        "node": {
            "package_file": "package.json",
            "lock_files": ["package-lock.json", "pnpm-lock.yaml", "yarn.lock"],
            "allow_loose_ranges": False,
        }
    },
    "complexity": {"max_fn_lines": 60, "max_file_lines": 600, "max_nesting": 4},
    "exclude": ["dist/**", "vendor/**", "**/*.min.js"],
}


@dataclass
class Config:
    data: Dict[str, Any] = field(default_factory=lambda: DEFAULT_CONFIG.copy())


def load_config(repo_root: str) -> Config:
    path = os.path.join(repo_root, ".techdebt.yml")
    merged = DEFAULT_CONFIG.copy()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                user = yaml.safe_load(f) or {}
                for k, v in user.items():
                    if isinstance(v, dict) and k in merged:
                        merged[k].update(v)
                    else:
                        merged[k] = v
            except Exception:
                pass
    return Config(merged)