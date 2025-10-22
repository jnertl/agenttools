"""Helpers for posting comments to GitHub issues.

This module provides a small convenience function `send_issue_comment` that
composes a comment from a few fields (title, body, action, issue_url) and
posts it to the GitHub Issues Comments API.

It uses the GITHUB_TOKEN environment variable by default but accepts an
optional `token` argument for override. For tests or dry runs, set
`dry_run=True` to get the composed payload without making network calls.
"""

from __future__ import annotations

import os
from typing import Optional, Dict, Any
import json

import requests

GITHUB_API_BASE = "https://api.github.com"


def _compose_comment(issue_number: int, title: Optional[str], body: Optional[str], action: Optional[str], issue_url: Optional[str]) -> str:
    """Return a Markdown comment string composed from provided pieces."""
    parts = []
    if action:
        parts.append(f"**Action:** {action}")
    if title:
        parts.append(f"**Issue:** {title}")
    if body:
        parts.append("---")
        parts.append(body)
    if issue_url:
        parts.append(f"[View issue]({issue_url})")

    parts.append(f"_Posted by automation for issue #{issue_number}_")
    return "\n\n".join(parts)


def send_issue_comment(
    repo_full_name: str,
    issue_number: int,
    title: Optional[str] = None,
    body: Optional[str] = None,
    action: Optional[str] = None,
    issue_url: Optional[str] = None,
    token: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Post a comment to a GitHub issue.

    Args:
        repo_full_name: repository full name like 'owner/repo'
        issue_number: the issue number to comment on
        title: optional issue title (included in the comment body)
        body: optional issue body or additional text
        action: optional action label to include in the comment
        issue_url: optional direct URL to the issue (will be included)
        token: optional GitHub token; if not provided uses GITHUB_TOKEN env var
        dry_run: if True, do not perform network call; return composed payload

    Returns:
        A dict with keys: 'url' (comment url if posted), 'payload' (dict posted),
        and 'response' (requests.Response-like dict when not dry_run).

    Raises:
        ValueError: on missing required inputs.
        requests.HTTPError: when the GitHub API returns 4xx/5xx.
    """

    if not repo_full_name or "/" not in repo_full_name:
        raise ValueError("repo_full_name must be in the form 'owner/repo'")

    if not issue_number or issue_number <= 0:
        raise ValueError("issue_number must be a positive integer")

    token = token or os.getenv("GITHUB_TOKEN")
    if not token and not dry_run:
        raise ValueError("GITHUB_TOKEN must be set in environment or passed as token")

    comment_text = _compose_comment(issue_number, title, body, action, issue_url)
    payload = {"body": comment_text}

    if dry_run:
        return {"url": None, "payload": payload, "response": None}

    owner, repo = repo_full_name.split("/", 1)
    post_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{issue_number}/comments"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }

    resp = requests.post(post_url, headers=headers, data=json.dumps(payload), timeout=10)

    try:
        resp.raise_for_status()
    except Exception:
        # Attach useful debugging information
        msg = f"Failed to post comment: {resp.status_code} {resp.text}"
        raise requests.HTTPError(msg, response=resp)

    return {"url": resp.json().get("html_url"), "payload": payload, "response": resp.json()}
