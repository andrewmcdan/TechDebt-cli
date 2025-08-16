import argparse
from .scanner import scan_repo
from .renderer import render_markdown
from .utils import write_json, find_repo_root
from .config import load_config


def main():
    parser = argparse.ArgumentParser(prog="techdebt", description="Tech Debt CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    scan = sub.add_parser("scan", help="Scan a repository")
    scan.add_argument("path", help="Path to repo (or any child path)")
    scan.add_argument("--markdown", action="store_true", help="Emit TECH_DEBT.md")
    scan.add_argument("--json", action="store_true", help="Emit tech-debt.json")
    scan.add_argument("--issues", action="store_true", help="Create umbrella GitHub issue via gh")
    scan.add_argument("--owner", default=None, help="GitHub username for issue assignment")
    scan.add_argument("--since-days", type=int, default=30, help="Git churn window (days)")
    scan.add_argument("--max-items", type=int, default=2000, help="Safety cap on number of items")

    args = parser.parse_args()

    repo_root = find_repo_root(args.path)
    cfg = load_config(repo_root)
    result = scan_repo(repo_root, cfg, since_days=args.since_days, max_items=args.max_items)

    if args.json:
        write_json(result, repo_root)

    if args.markdown:
        render_markdown(result, repo_root)

    if args.issues:
        try:
            from .utils import create_umbrella_issue
            create_umbrella_issue(result, repo_root, assignee=args.owner)
        except Exception as e:
            print(f"[warn] Failed to create GitHub issue: {e}")


if __name__ == "__main__":
    main()