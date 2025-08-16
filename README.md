# techdebt-cli

A fast, zero-infra CLI that scans your repo and creates a Markdown dashboard (**TECH_DEBT.md**) and a machine-readable JSON (**tech-debt.json**).

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Usage
```bash
techdebt scan . --markdown --json [--issues --owner your-github-username]
```

Respects .gitignore

Emits TECH_DEBT.md (Markdown report) and/or tech-debt.json

Optional: creates a single umbrella GitHub issue checklist (requires gh CLI installed and authenticated)

## Config

Place a .techdebt.yml at repo root to tweak weights, markers, complexity thresholds, etc.