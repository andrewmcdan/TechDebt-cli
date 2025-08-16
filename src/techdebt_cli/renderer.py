from __future__ import annotations
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape


def render_markdown(result, repo_root: str):
    tmpl_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(tmpl_dir), autoescape=select_autoescape())
    tmpl = env.get_template("report.md.j2")
    md = tmpl.render(**result)
    path = os.path.join(repo_root, "TECH_DEBT.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {path}")