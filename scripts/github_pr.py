#!/usr/bin/env python3
"""CLI wrapper to compute a git diff and create a GitHub Pull Request.

Examples:
  # Dry-run showing the diff and composed PR payload
  ./scripts/github_pr.py --git-dir /path/to/repo --repo https://github.com/owner/repo.git --base main --head issue_123 --dry-run

  # Create a PR (requires GITHUB_TOKEN)
  ./scripts/github_pr.py --git-dir /path/to/repo --repo owner/repo --base main --head issue_123 --title "Fix bug" --body-file pr_body.md
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional
import subprocess

# Make project root importable when running script directly
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from agenttools.github_pr import get_git_diff, parse_repo_full_name, create_pull_request, create_pr_from_git, push_branch_via_api, push_tree_via_api


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create GitHub PR from local git branch (API-only)")
    parser.add_argument("--git-dir", required=True, help="Path to local git repository (used as source of files)")
    parser.add_argument("--repo", required=True, help="GitHub repo (owner/repo or URL)")
    parser.add_argument("--base", default="main", help="Base branch to merge into")
    parser.add_argument("--head", required=True, help="Head branch name with your changes")
    parser.add_argument("--title", help="PR title")
    parser.add_argument("--body", help="PR body text")
    parser.add_argument("--body-file", help="Read PR body from file")
    parser.add_argument("--token", help="GitHub token (overrides GITHUB_TOKEN env var)")
    parser.add_argument("--dry-run", action="store_true", help="Do not call GitHub API; print payload")
    parser.add_argument("--local", action="store_true", help="Compare local branches (no git fetch / origin refs). Uses base..head locally")
    parser.add_argument("--no-push", action="store_true", help="Do not apply changes to the remote via GitHub API (push is default)")
    parser.add_argument("--commit-message", help="Commit message to use when committing staged changes (default auto)")

    args = parser.parse_args(argv)

    body = args.body
    if args.body_file:
        body = Path(args.body_file).read_text(encoding="utf-8")

    repo_full_name = parse_repo_full_name(args.repo)

    token = args.token or os.getenv("GITHUB_TOKEN")
    if not token and not args.dry_run and not args.no_push:
        print("Error: --token or GITHUB_TOKEN must be provided to apply changes via the GitHub API.")
        return 2

    print("API-only mode: will apply changes via GitHub API (requires token). Use --no-push to skip applying changes.")

    # Push branch to origin by default (unless --no-push). Use GitHub API to apply file-level changes.
    if not args.no_push:
        try:
            api_push_res = push_tree_via_api(args.git_dir, args.repo, args.base, args.head, token=token, dry_run=args.dry_run)
            print("Pushed branch via GitHub API. Branch URL:", api_push_res.get("branch_url"))
        except Exception as e:
            print(f"Failed to push branch {args.head} via GitHub API: {e}")
            return 4

    # Create PR: if we used API-only push, we already have operations available in api_push_res
    # Build a PR body from provided body or from the API ops summary
    if body:
        pr_body = body
    else:
        ops = api_push_res.get("operations") or []
        summary_lines = []
        for op in ops:
            summary_lines.append(f"{op.get('op')}: {op.get('path', op.get('ref', ''))}")
        pr_body = "Automated PR (API push)\n\nChanges:\n" + "\n".join(summary_lines)

    res = create_pull_request(repo_full_name, args.head, base=args.base, title=args.title, body=pr_body, token=token, dry_run=args.dry_run)

    if isinstance(res, str):
        print(res)
        return 0

    if args.dry_run:
        print("--- DRY RUN payload ---")
        print(res["payload"])   
        print("Branch URL:", res.get("branch_url"))
    else:
        pr_url = res.get("pr_url") or res.get("url")
        print("PR created:", pr_url)
        print("Branch URL:", res.get("branch_url"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
