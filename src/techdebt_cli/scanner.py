from __future__ import annotations
import os, re, json
from typing import Dict, Any, List
from glob import glob
from .signals import DebtItem
from .utils import (
    load_gitignore, iter_files, is_text_file, git_commit_sha, git_last_modified, git_churn,
)
from .scoring import compute_score, bucket
from .config import Config

# Simple deprecated API regexes (extend per language)
DEPRECATED_JS = [r"\bfs\.rmdir\b", r"\bnew\s+Buffer\s*\("]
DEPRECATED_PY = [r"\basyncio\.get_event_loop\s*\(", r"\blogging\.warn\s*\("]

LINT_SUPPRESS = [r"eslint-disable", r"#\s*noqa", r"@ts-ignore"]

INLINE_OWNER = re.compile(r"@([a-z0-9_-]+)", re.I)
INLINE_PRIORITY = re.compile(r"\[(P\d)\]", re.I)


def norm(v: float, max_v: float) -> float:
    if max_v <= 0:
        return 0.0
    return max(0.0, min(1.0, v / max_v))


def scan_repo(repo_root: str, cfg: Config, since_days: int = 30, max_items: int = 2000) -> Dict[str, Any]:
    ignore = load_gitignore(repo_root)
    excludes = cfg.data.get("exclude", [])
    weights = cfg.data.get("weights", {})

    # Precompute churn
    churn_map = git_churn(repo_root, since_days)

    items: List[DebtItem] = []

    # Walk files, collect signals
    for abspath in iter_files(repo_root, ignore, excludes):
        rel = os.path.relpath(abspath, repo_root)
        try:
            if not is_text_file(abspath):
                continue
            with open(abspath, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
        except Exception:
            continue

        lines = txt.splitlines()
        loc = sum(1 for ln in lines if ln.strip())

        # Inline markers
        for m in re.finditer(r"(TODO|FIXME|HACK|XXX|BUG|OPTIMIZE).*", txt):
            line_no = txt.count("\n", 0, m.start()) + 1
            line = m.group(0)[:240]
            owner = None
            prio = None
            mo = INLINE_OWNER.search(line)
            if mo:
                owner = mo.group(1)
            mp = INLINE_PRIORITY.search(line)
            if mp:
                prio = mp.group(1).upper()
            comp = {
                "inline_priority": 1.0 if (prio and prio.upper() == "P1") else 0.5 if prio else 0.2,
                "age_days": 0.0,
                "churn": norm(churn_map.get(rel, 0), 2000),
                "complexity": norm(loc, 1000),
                "deps_outdated": 0.0,
                "no_tests": 0.0,
                "lint_suppress": 0.0,
                "deprecated": 0.0,
            }
            lm = git_last_modified(repo_root, rel)
            if lm:
                from datetime import datetime

                age_days = (datetime.utcnow() - lm).days
                comp["age_days"] = norm(age_days, 365)
            score = compute_score(comp, weights)
            item = DebtItem(
                path=rel,
                kind="inline_marker",
                score=score,
                meta={"line": line_no, "snippet": line, "components": comp},
                owner=owner,
                priority=None,
            )
            items.append(item)

        # Lint suppressions
        if any(re.search(pat, txt) for pat in LINT_SUPPRESS):
            comp = {
                "inline_priority": 0.0,
                "age_days": 0.0,
                "churn": norm(churn_map.get(rel, 0), 2000),
                "complexity": norm(loc, 1000),
                "deps_outdated": 0.0,
                "no_tests": 0.0,
                "lint_suppress": 1.0,
                "deprecated": 0.0,
            }
            score = compute_score(comp, weights)
            items.append(
                DebtItem(path=rel, kind="lint_suppress", score=score, meta={"lines": loc, "components": comp})
            )

        # Deprecated API usage
        pats = DEPRECATED_JS + DEPRECATED_PY
        hits = 0
        for pat in pats:
            for _ in re.finditer(pat, txt):
                hits += 1
        if hits:
            comp = {
                "inline_priority": 0.0,
                "age_days": 0.0,
                "churn": norm(churn_map.get(rel, 0), 2000),
                "complexity": norm(loc, 1000),
                "deps_outdated": 0.0,
                "no_tests": 0.0,
                "lint_suppress": 0.0,
                "deprecated": min(1.0, hits / 5.0),
            }
            score = compute_score(comp, weights)
            items.append(
                DebtItem(path=rel, kind="deprecated", score=score, meta={"hits": hits, "components": comp})
            )

        # Generated / built artifacts
        base = os.path.basename(rel).lower()
        if rel.startswith("dist/") or base.endswith(".min.js"):
            comp = {
                "inline_priority": 0.0,
                "age_days": 0.0,
                "churn": 0.0,
                "complexity": norm(loc, 1000),
                "deps_outdated": 0.0,
                "no_tests": 0.0,
                "lint_suppress": 0.0,
                "deprecated": 0.0,
            }
            score = compute_score(comp, weights)
            items.append(
                DebtItem(path=rel, kind="generated_artifact", score=score, meta={"components": comp})
            )

        # Config drift: Dockerfile latest, GH Actions not pinned
        if os.path.basename(rel).lower() == "dockerfile":
            for ln in lines:
                if ln.strip().lower().startswith("from ") and ":latest" in ln:
                    comp = {
                        "inline_priority": 0.0,
                        "age_days": 0.0,
                        "churn": 0.0,
                        "complexity": 0.0,
                        "deps_outdated": 0.0,
                        "no_tests": 0.0,
                        "lint_suppress": 0.0,
                        "deprecated": 0.3,
                    }
                    score = compute_score(comp, weights)
                    items.append(
                        DebtItem(
                            path=rel, kind="config_drift", score=score, meta={"line": ln.strip(), "components": comp}
                        )
                    )
        if rel.startswith(".github/workflows/") and rel.endswith((".yml", ".yaml")):
            for ln in lines:
                if "uses:" in ln:
                    if not re.search(r"@([a-f0-9]{40})\\b", ln):
                        comp = {
                            "inline_priority": 0.0,
                            "age_days": 0.0,
                            "churn": 0.0,
                            "complexity": 0.0,
                            "deps_outdated": 0.0,
                            "no_tests": 0.0,
                            "lint_suppress": 0.0,
                            "deprecated": 0.3,
                        }
                        score = compute_score(comp, weights)
                        items.append(
                            DebtItem(
                                path=rel, kind="config_drift", score=score, meta={"line": ln.strip(), "components": comp}
                            )
                        )

    # Dependency risk (Node)
    pkg_json = os.path.join(repo_root, "package.json")
    if os.path.exists(pkg_json):
        try:
            pkg = json.load(open(pkg_json, "r", encoding="utf-8"))
        except Exception:
            pkg = {}
        deps = {}
        for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
            deps.update(pkg.get(key, {}))
        # Loose ranges
        for name, ver in deps.items():
            if any(ch in str(ver) for ch in ["^", "~", "*", "x", "X"]):
                comp = {
                    "inline_priority": 0.0,
                    "age_days": 0.0,
                    "churn": 0.0,
                    "complexity": 0.0,
                    "deps_outdated": 1.0,
                    "no_tests": 0.0,
                    "lint_suppress": 0.0,
                    "deprecated": 0.0,
                }
                score = compute_score(comp, weights)
                items.append(
                    DebtItem(
                        path="package.json",
                        kind="dep_risk",
                        score=score,
                        meta={"dep": name, "version": ver, "reason": "loose_range", "components": comp},
                    )
                )
        # Unused deps (naive)
        import_re = re.compile(r"from\\s+['\"]([^'\"]+)['\"]|require\\(\\s*['\"]([^'\"]+)['\"]\\s*\\)")
        used = set()
        for abspath in iter_files(repo_root, ignore, excludes):
            if not abspath.endswith((".js", ".jsx", ".ts", ".tsx")):
                continue
            try:
                txt = open(abspath, "r", encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for m in import_re.finditer(txt):
                mod = m.group(1) or m.group(2)
                if mod and not mod.startswith("."):
                    root = mod.split("/", 2)[:2] if mod.startswith("@") else [mod.split("/", 1)[0]]
                    used.add("/".join(root) if isinstance(root, list) else root)
        for name in deps.keys():
            if name not in used:
                comp = {
                    "inline_priority": 0.0,
                    "age_days": 0.0,
                    "churn": 0.0,
                    "complexity": 0.0,
                    "deps_outdated": 0.7,
                    "no_tests": 0.0,
                    "lint_suppress": 0.0,
                    "deprecated": 0.0,
                }
                score = compute_score(comp, weights)
                items.append(
                    DebtItem(
                        path="package.json",
                        kind="dep_risk",
                        score=score,
                        meta={"dep": name, "reason": "possibly_unused", "components": comp},
                    )
                )

    # Test gaps by convention
    conv = (cfg.data.get("tests") or {}).get("convention") or {}
    src_globs = conv.get("src_globs", [])
    test_globs = conv.get("test_globs", [])
    test_set = set()
    for g in test_globs:
        for p in glob(os.path.join(repo_root, g), recursive=True):
            test_set.add(os.path.relpath(p, repo_root))
    for g in src_globs:
        for p in glob(os.path.join(repo_root, g), recursive=True):
            rel = os.path.relpath(p, repo_root)
            base = os.path.basename(rel)
            if base.endswith((".ts", ".py")):
                stem = base.rsplit(".", 1)[0]
                candidates = [
                    rel.replace("/src/", "/tests/").replace(".ts", ".test.ts"),
                    rel.replace("/app/", "/tests/").replace(".py", ".py"),
                    os.path.join("tests", f"{stem}.test.ts"),
                    os.path.join("tests", base),
                ]
                if not any(c in test_set for c in candidates):
                    comp = {
                        "inline_priority": 0.0,
                        "age_days": 0.0,
                        "churn": 0.0,
                        "complexity": 0.5,
                        "deps_outdated": 0.0,
                        "no_tests": 1.0,
                        "lint_suppress": 0.0,
                        "deprecated": 0.0,
                    }
                    score = compute_score(comp, weights)
                    items.append(
                        DebtItem(
                            path=rel,
                            kind="test_gap",
                            score=score,
                            meta={"expected_tests": candidates, "components": comp},
                        )
                    )

    # Sort by score and cap
    items.sort(key=lambda it: it.score, reverse=True)
    items = items[:max_items]

    json_items = []
    totals = {"count": len(items), "by_kind": {}, "avg_score": 0.0}
    if items:
        avg = sum(it.score for it in items) / len(items)
        totals["avg_score"] = round(avg, 2)
        for it in items:
            totals["by_kind"][it.kind] = totals["by_kind"].get(it.kind, 0) + 1
            meta = dict(it.meta)
            meta["priority_bucket"] = bucket(it.score)
            json_items.append(
                {
                    "path": it.path,
                    "kind": it.kind,
                    "score": it.score,
                    "meta": meta,
                    "owner": it.owner,
                    "status": it.status,
                }
            )

    result = {
        "repo_root": repo_root,
        "commit_sha": git_commit_sha(repo_root),
        "summary": totals,
        "items": json_items,
    }
    return result