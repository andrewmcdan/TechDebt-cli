from __future__ import annotations
import os, subprocess, json, re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Iterable
from pathspec import PathSpec

TEXT_EXT = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yml", ".yaml", ".md", ".txt", ".toml", ".ini", ".env",
    ".java", ".go", ".rs", ".cpp", ".c", ".h", ".hpp", ".cs", ".rb", ".php", ".sh", ".bat", ".ps1", ".dockerfile",
}


def find_repo_root(start: str) -> str:
    start = os.path.abspath(start)
    p = start
    while p and p != os.path.dirname(p):
        if os.path.exists(os.path.join(p, ".git")):
            return p
        p = os.path.dirname(p)
    return start


def load_gitignore(repo_root: str) -> PathSpec:
    path = os.path.join(repo_root, ".gitignore")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return PathSpec.from_lines("gitwildmatch", f)
    return PathSpec.from_lines("gitwildmatch", [])


def is_text_file(path: str) -> bool:
    _, ext = os.path.splitext(path.lower())
    if ext in TEXT_EXT:
        return True
    try:
        with open(path, "rb") as f:
            chunk = f.read(2048)
        if b"\0" in chunk:
            return False
        return True
    except Exception:
        return False


def iter_files(repo_root: str, ignore: PathSpec, excludes: List[str]) -> Iterable[str]:
    exclude_spec = PathSpec.from_lines("gitwildmatch", excludes or [])
    for root, _, files in os.walk(repo_root):
        for name in files:
            rel = os.path.relpath(os.path.join(root, name), repo_root)
            if ignore.match_file(rel) or exclude_spec.match_file(rel):
                continue
            yield os.path.join(repo_root, rel)


def run(cmd: List[str], cwd: Optional[str] = None, timeout: int = 30) -> str:
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            text=True,
        )
        return res.stdout
    except Exception:
        return ""


def git_commit_sha(repo_root: str) -> Optional[str]:
    out = run(["git", "rev-parse", "HEAD"], cwd=repo_root).strip()
    return out or None


def git_last_modified(repo_root: str, rel_path: str) -> Optional[datetime]:
    out = run(["git", "log", "-1", "--format=%ct", "--", rel_path], cwd=repo_root).strip()
    if out.isdigit():
        return datetime.utcfromtimestamp(int(out))
    return None


def git_churn(repo_root: str, since_days: int) -> Dict[str, int]:
    since = (datetime.utcnow() - timedelta(days=since_days)).strftime("%Y-%m-%d")
    out = run(["git", "log", f"--since={since}", "--numstat", "--pretty=format:---%H"], cwd=repo_root)
    churn: Dict[str, int] = {}
    for line in out.splitlines():
        if re.match(r"^\d+\t\d+\t", line):
            adds, dels, path = line.split("\t", 2)
            try:
                churn[path] = churn.get(path, 0) + int(adds) + int(dels)
            except ValueError:
                pass
    return churn


def write_json(result: Any, repo_root: str):
    path = os.path.join(repo_root, "tech-debt.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"Wrote {path}")


def create_umbrella_issue(result: Any, repo_root: str, assignee: Optional[str] = None):
    items = result.get("items", [])[:50]
    title = "Tech Debt Report"
    body_lines = ["Automated tech debt report. Top items:", ""]
    for it in items[:25]:
        path = it.get("path")
        kind = it.get("kind")
        score = it.get("score")
        body_lines.append(f"- [ ] {path} — {kind} — score {score}")
    body = "\n".join(body_lines)
    cmd = ["gh", "issue", "create", "-t", title, "-b", body]
    if assignee:
        cmd.extend(["-a", assignee])
    out = run(cmd, cwd=repo_root)
    if out.strip():
        print(out.strip())
    else:
        print("gh issue create: no output (check auth/repo visibility)")