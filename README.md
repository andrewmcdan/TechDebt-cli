# techdebt-cli

A fast, zero-infra CLI that scans your repo and creates a Markdown dashboard (**TECH_DEBT.md**) and a machine-readable JSON (**tech-debt.json**).

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## CLI Options

```bash
python -m techdebt_cli scan PATH [options]
```

| Option | Description |
|--------|-------------|
| `--markdown` | Emit `TECH_DEBT.md` report. |
| `--json` | Emit `tech-debt.json` report. |
| `--issues` | Create an umbrella GitHub issue (requires `gh`). |
| `--owner USER` | Assign the created GitHub issue to `USER`. |
| `--since-days N` | Git churn window in days (default: 30). |
| `--max-items N` | Safety cap on number of debt items (default: 2000). |

## Sample Output

### `TECH_DEBT.md`

```markdown
# Tech Debt Report

**Repo:** `/workspace/TechDebt-cli`
**Commit:** `4ba0cc531cd47b5897053ec8f1a95a92f9466362`
**Items:** 7
**Average score:** 61.35

## Top 10 Hotspots
| Path | Kind | Score | Notes |
|------|------|-------|-------|
| `.techdebt.yml` | `inline_marker` | **73.85** | TODO [P1] |
| `src/techdebt_cli/scanner.py` | `lint_suppress` | **69.30** |  |
```

### `tech-debt.json`

```json
{
  "repo_root": "/workspace/TechDebt-cli",
  "commit_sha": "4ba0cc531cd47b5897053ec8f1a95a92f9466362",
  "summary": {
    "count": 7,
    "by_kind": { "inline_marker": 6, "lint_suppress": 1 },
    "avg_score": 61.35
  },
  "items": [
    {
      "path": ".techdebt.yml",
      "kind": "inline_marker",
      "score": 73.85,
      "meta": { "...": "..." }
    }
  ]
}
```

## Configuration (`.techdebt.yml`)

Create a `.techdebt.yml` at the repo root to tweak scoring and behaviour:

```yaml
weights:
  inline_priority: 1.0
  complexity: 0.7
markers:
  - pattern: "(TODO|FIXME|HACK|XXX|BUG|OPTIMIZE)"
    priority_from: "\\[(P\\d)\\]"
    owner_from: "@([a-z0-9_-]+)"
tests:
  convention:
    src_globs: ["src/**/*.ts", "app/**/*.py"]
    test_globs: ["**/*.test.ts", "tests/**/*.py"]
exclude:
  - "dist/**"
  - "vendor/**"
```

## Quick Start

1. **Install** the CLI (see above).
2. **Scan** your repository:

   ```bash
   python -m techdebt_cli scan . --markdown --json
   ```

3. **Review `TECH_DEBT.md`** for a human-readable dashboard and **`tech-debt.json`** for machine-readable data.
4. Optionally run with `--issues --owner your-github-username` to open a GitHub issue summarising top items.

---

Respects `.gitignore`.

Emits `TECH_DEBT.md` (Markdown report) and/or `tech-debt.json`.

Place a .techdebt.yml at repo root to tweak weights, markers, complexity thresholds, etc.

## CMake

This project can be added to a larger CMake build and run as a custom target.

```cmake
add_subdirectory(path/to/TechDebt-cli)
```

Running the `techdebt` target generates `TECH_DEBT.md` and `tech-debt.json` for the
directory specified by `TECHDEBT_SCAN_DIR` (defaults to the top-level source tree):

```bash
cmake --build . --target techdebt
```

You may override the scan path during configuration:

```bash
cmake -DTECHDEBT_SCAN_DIR=/path/to/scan -S . -B build
```
