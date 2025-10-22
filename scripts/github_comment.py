#!/usr/bin/env python3
"""Small CLI wrapper to post a comment to a GitHub issue using agenttools.github_issues.

Usage examples:
    ./scripts/github_comment.py --repo owner/repo --issue 42 --body "Quick note" --action triage
    cat note.md | ./scripts/github_comment.py --repo owner/repo --issue 42 --stdin
"""

import sys
import argparse
from typing import Optional

from agenttools.github_issues import send_issue_comment


def main(argv=None):
    parser = argparse.ArgumentParser(description="Post a comment to a GitHub issue")
    parser.add_argument("--repo", required=True, help="Repository full name, e.g. owner/repo")
    parser.add_argument("--issue", required=True, type=int, help="Issue number")
    parser.add_argument("--title", help="Issue title to include in the comment")
    parser.add_argument("--body", help="Comment body text. If not provided and --stdin not set, body is empty")
    parser.add_argument("--stdin", action="store_true", help="Read comment body from stdin")
    parser.add_argument("--action", help="Action to include in the comment (e.g. triage, fix)")
    parser.add_argument("--issue-url", help="Direct issue URL to include in the comment")
    parser.add_argument("--token", help="GitHub token (overrides GITHUB_TOKEN env var)")
    parser.add_argument("--dry-run", action="store_true", help="Do not perform network call; print payload")

    args = parser.parse_args(argv)

    body: Optional[str] = args.body
    if args.stdin:
        body = sys.stdin.read()

    res = send_issue_comment(
        repo_full_name=args.repo,
        issue_number=args.issue,
        title=args.title,
        body=body,
        action=args.action,
        issue_url=args.issue_url,
        token=args.token,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("--- DRY RUN: payload ---")
        print(res["payload"]["body"])
        return 0

    print("Posted comment:", res.get("url"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
