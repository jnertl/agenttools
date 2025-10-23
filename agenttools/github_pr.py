"""Utilities to create a GitHub Pull Request from a local git repo/branch.

This module provides:
- get_git_diff(git_dir, base_branch, head_branch) -> str
- parse_repo_full_name(repo_url) -> str (owner/repo)
- create_pull_request(repo_full_name, head, base, title, body, token, dry_run)

The functions use `git` via subprocess for diffs and the GitHub REST API
for creating the pull request.
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Optional, Tuple, Dict, Any
import json

import requests
import base64
import hashlib

GITHUB_API_BASE = "https://api.github.com"


def parse_repo_full_name(repo_url: str) -> str:
    """Return 'owner/repo' parsed from a git remote URL.

    Supports:
      - https://github.com/owner/repo.git
      - git@github.com:owner/repo.git
      - owner/repo
    """
    if not repo_url:
        raise ValueError("repo_url is required")

    # If already owner/repo
    if re.match(r"^[\w.-]+\/[\w.-]+$", repo_url):
        return repo_url

    m = re.match(r"^(?:https?://github.com/|git@github.com:)([^/]+/[^/.]+)(?:\.git)?$", repo_url)
    if m:
        return m.group(1)

    raise ValueError(f"Could not parse repository full name from '{repo_url}'")


def get_git_diff(git_dir: str, base_branch: str, head_branch: Optional[str] = None, max_bytes: int = 200_000, use_remote: bool = True) -> str:
    """Return the git diff between base_branch and head_branch in the given git_dir.

    The function does a `git fetch` and then runs:
      git -C <git_dir> diff --no-color origin/<base_branch>..origin/<head_branch>

    If the diff is larger than `max_bytes`, it will be truncated with a note.
    """
    if not os.path.isdir(git_dir):
        raise ValueError(f"git_dir not found: {git_dir}")

    # If using remote refs, fetch from origin and compare origin/<base>..origin/<head>
    if use_remote:
        try:
            subprocess.run(["git", "-C", git_dir, "fetch", "--all"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"git fetch failed: {e.stderr.decode('utf-8', 'ignore')}")

        # If head_branch not provided, detect the current branch in the repo
        if not head_branch:
            try:
                proc = subprocess.run(["git", "-C", git_dir, "rev-parse", "--abbrev-ref", "HEAD"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                head_branch = proc.stdout.decode("utf-8", errors="replace").strip()
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"failed to determine current branch: {e.stderr.decode('utf-8', 'ignore')}")

        diff_cmd = ["git", "-C", git_dir, "diff", "--no-color", f"origin/{base_branch}..origin/{head_branch}"]
    else:
        # Local comparison: do not fetch; compare local refs base..head (or HEAD if head not given)
        if not head_branch:
            try:
                proc = subprocess.run(["git", "-C", git_dir, "rev-parse", "--abbrev-ref", "HEAD"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                head_branch = proc.stdout.decode("utf-8", errors="replace").strip()
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"failed to determine current branch: {e.stderr.decode('utf-8', 'ignore')}")

        # Compare committed changes between branches
        diff_cmd = ["git", "-C", git_dir, "diff", "--no-color", f"{base_branch}..{head_branch}"]
    try:
        proc = subprocess.run(diff_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        diff = proc.stdout.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        # git diff returns exit code 1 when diffs exist; handle by capturing stdout
        diff = e.stdout.decode("utf-8", errors="replace") if hasattr(e, 'stdout') and e.stdout else ''

    if len(diff.encode("utf-8")) > max_bytes:
        note = f"\n\n[Diff truncated: original size {len(diff)} chars]\n"
        # keep only first max_bytes worth of characters (approx)
        truncated = diff.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
        return truncated + note

    return diff


def create_pull_request(
    repo_full_name: str,
    head: str,
    base: str = "main",
    title: Optional[str] = None,
    body: Optional[str] = None,
    token: Optional[str] = None,
    draft: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Create a pull request on GitHub.

    Args:
        repo_full_name: 'owner/repo'
        head: branch name in the repo (e.g., 'issue_123')
        base: base branch to target (default 'main')
        title: PR title (if omitted a default is used)
        body: PR body (optional)
        token: optional GitHub token; if omitted GITHUB_TOKEN env var is used
        draft: create PR as draft
        dry_run: if True, do not call the API; return payload

    Returns:
        dict containing API response JSON when not dry_run or composed payload for dry_run
    """
    if "/" not in repo_full_name:
        raise ValueError("repo_full_name must be 'owner/repo'")

    token = token or os.getenv("GITHUB_TOKEN")
    if not token and not dry_run:
        raise ValueError("GITHUB_TOKEN must be set in environment or passed as token")

    owner, repo = repo_full_name.split("/", 1)
    pr_title = title or f"Automated PR: {head} -> {base}"
    payload = {"title": pr_title, "head": head, "base": base, "body": body or "", "draft": draft}

    branch_url = f"https://github.com/{repo_full_name}/tree/{head}"
    if dry_run:
        return {"payload": payload, "url": None, "pr_url": None, "branch_url": branch_url, "response": None}

    post_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "Content-Type": "application/json"}

    resp = requests.post(post_url, headers=headers, data=json.dumps(payload), timeout=10)
    try:
        resp.raise_for_status()
    except Exception:
        raise requests.HTTPError(f"Failed to create PR: {resp.status_code} {resp.text}", response=resp)

    pr_url = resp.json().get("html_url")
    return {"payload": payload, "url": pr_url, "pr_url": pr_url, "branch_url": branch_url, "response": resp.json()}


def create_pr_from_git(
    git_dir: str,
    repo_url: str,
    base: str,
    head: str,
    title: Optional[str] = None,
    body: Optional[str] = None,
    token: Optional[str] = None,
    dry_run: bool = False,
    use_remote: bool = True,
) -> Any:
    """Helper that computes git diff and creates a PR only if changes exist.

    Returns a dict (same shape as create_pull_request) when a PR is created or
    the string "No changes detected; no PR necessary." when there is nothing to do.
    """
    diff = get_git_diff(git_dir, base, head, use_remote=use_remote)
    if not diff.strip():
        return "No changes detected; no PR necessary."

    repo_full_name = parse_repo_full_name(repo_url)

    pr_body = body or f"Automated PR from branch {head}\n\nDiff:\n```\n{diff[:8000]}\n```"
    return create_pull_request(repo_full_name=repo_full_name, head=head, base=base, title=title, body=pr_body, token=token, dry_run=dry_run)


def push_branch_via_api(git_dir: str, repo_url: str, base: str, head: str, token: Optional[str] = None, timeout: int = 10) -> Dict[str, Any]:
    """Push changes from local branch `head` into the remote repository using the GitHub API.

    This implements a file-level push using the Contents API: it inspects
    `git -C <git_dir> diff --name-status <base>.. <head>` to discover added,
    modified and deleted files and applies those changes on the target branch
    via the GitHub REST API.

    Limitations:
    - Renames and copy operations are treated as delete+add.
    - Large changes or many files may hit rate/size limits; in that case use regular git push.
    - This replays the final content of files as present on disk in `git_dir`.

    Returns a dict with 'branch_url' and a list of 'operations' performed.
    """
    token = token or os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN must be set in environment or passed as token")

    repo_full = parse_repo_full_name(repo_url)
    owner, repo = repo_full.split("/", 1)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    # Ensure branch exists: get base commit SHA then create head ref if missing
    ref_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/ref/heads/{base}"
    r = requests.get(ref_url, headers=headers, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to get base ref {base}: {r.status_code} {r.text}")
    base_sha = r.json()["object"]["sha"]

    # Try to get head ref; if 404 create it from base
    head_ref_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/ref/heads/{head}"
    r = requests.get(head_ref_url, headers=headers, timeout=timeout)
    if r.status_code == 404:
        create_ref_payload = {"ref": f"refs/heads/{head}", "sha": base_sha}
        r = requests.post(f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/refs", headers=headers, json=create_ref_payload, timeout=timeout)
        r.raise_for_status()
    elif r.status_code != 200:
        r.raise_for_status()

    # Gather changed files using local git
    try:
        proc = subprocess.run(["git", "-C", git_dir, "diff", "--name-status", f"{base}..{head}"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        name_status = proc.stdout.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"git diff failed: {e.stderr.decode('utf-8', 'ignore')}")

    ops = []
    for line in name_status.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        # handle rename: status like 'R100'
        if status.startswith('R'):
            # rename: parts = [Rxxx, old_path, new_path]
            if len(parts) >= 3:
                old_path = parts[1]
                new_path = parts[2]
                # implement as delete old + add new
                actions = [("delete", old_path), ("add", new_path)]
            else:
                continue
        else:
            # statuses: A, M, D, C etc. We'll support A/M/D
            if len(parts) < 2:
                continue
            path = parts[1]
            if status == 'A' or status == 'M':
                actions = [("add", path)]
            elif status == 'D':
                actions = [("delete", path)]
            else:
                # unknown status: skip
                continue

        for action, path in actions:
            content_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
            if action == "delete":
                # Need to retrieve the sha of the file on the target branch
                q = requests.get(content_url, headers=headers, params={"ref": head}, timeout=timeout)
                if q.status_code == 200:
                    sha = q.json().get("sha")
                    payload = {"message": f"Delete {path}", "branch": head, "sha": sha}
                    resp = requests.delete(content_url, headers=headers, json=payload, timeout=timeout)
                    resp.raise_for_status()
                    ops.append({"op": "delete", "path": path, "response": resp.json()})
                else:
                    # file not present remotely; nothing to do
                    ops.append({"op": "delete", "path": path, "response": None})
            elif action == "add":
                full_path = os.path.join(git_dir, path)
                if not os.path.exists(full_path):
                    raise RuntimeError(f"Local file for add/update not found: {full_path}")
                # read file bytes and base64 encode
                with open(full_path, "rb") as fh:
                    data = fh.read()
                b64 = base64.b64encode(data).decode("utf-8")

                # Check if file exists on branch to know whether to include sha
                q = requests.get(content_url, headers=headers, params={"ref": head}, timeout=timeout)
                payload = {"message": f"Add/Update {path}", "content": b64, "branch": head}
                if q.status_code == 200:
                    payload["sha"] = q.json().get("sha")
                resp = requests.put(content_url, headers=headers, json=payload, timeout=timeout)
                resp.raise_for_status()
                ops.append({"op": "add_or_update", "path": path, "response": resp.json()})

    branch_url = f"https://github.com/{repo_full}/tree/{head}"
    return {"branch_url": branch_url, "operations": ops}


def push_tree_via_api(git_dir: str, repo_url: str, base: str, head: str, token: Optional[str] = None, dry_run: bool = False, timeout: int = 10) -> Dict[str, Any]:
    """Push the working tree in `git_dir` to `head` branch on GitHub using the Git Data and Contents APIs.

    Behavior:
    - Uses the Git Trees API to list files in the `base` branch on the remote.
    - Walks the local `git_dir` working tree (skips .git) and computes git blob SHA for each file.
    - Adds/updates files whose blob SHA differs, and deletes remote files not present locally.
    - Creates the head branch ref from base if it does not exist.

    Returns a dict with 'branch_url' and 'operations'. If `dry_run` is True, no mutating API calls are made; operations describe the planned actions.
    """
    token = token or os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN must be set in environment or passed as token")

    repo_full = parse_repo_full_name(repo_url)
    owner, repo = repo_full.split("/", 1)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    # Get base commit SHA and tree SHA
    ref_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/ref/heads/{base}"
    r = requests.get(ref_url, headers=headers, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to get base ref {base}: {r.status_code} {r.text}")
    base_commit_sha = r.json()["object"]["sha"]

    commit_resp = requests.get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/commits/{base_commit_sha}", headers=headers, timeout=timeout)
    commit_resp.raise_for_status()
    base_tree_sha = commit_resp.json()["tree"]["sha"]

    # Get remote tree recursively
    tree_resp = requests.get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{base_tree_sha}", headers=headers, params={"recursive": "1"}, timeout=timeout)
    tree_resp.raise_for_status()
    remote_entries = tree_resp.json().get("tree", [])
    remote_map = {e["path"]: e["sha"] for e in remote_entries if e["type"] == "blob"}

    # Build local file map (path -> blob_sha)
    local_map = {}
    for root, dirs, files in os.walk(git_dir):
        # skip .git
        dirs[:] = [d for d in dirs if d != ".git"]
        for fname in files:
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, git_dir).replace(os.path.sep, "/")
            # read bytes and compute git blob sha
            with open(full, "rb") as fh:
                data = fh.read()
            header = f"blob {len(data)}\0".encode("utf-8")
            sha = hashlib.sha1(header + data).hexdigest()
            local_map[rel] = {"sha": sha, "bytes": data}

    # Determine operations
    adds = []
    updates = []
    deletes = []
    for path, info in local_map.items():
        if path not in remote_map:
            adds.append(path)
        elif remote_map[path] != info["sha"]:
            updates.append(path)

    for path in remote_map:
        if path not in local_map:
            deletes.append(path)

    ops = []

    # Ensure head ref exists (create from base if missing)
    head_ref_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/ref/heads/{head}"
    r = requests.get(head_ref_url, headers=headers, timeout=timeout)
    if r.status_code == 404:
        if dry_run:
            ops.append({"op": "create_ref", "ref": head, "from": base_commit_sha})
        else:
            create_ref_payload = {"ref": f"refs/heads/{head}", "sha": base_commit_sha}
            rr = requests.post(f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/refs", headers=headers, json=create_ref_payload, timeout=timeout)
            rr.raise_for_status()
            ops.append({"op": "create_ref", "ref": head, "response": rr.json()})

    # Apply adds/updates
    for path in adds + updates:
        full = os.path.join(git_dir, path)
        data = local_map[path]["bytes"]
        b64 = base64.b64encode(data).decode("utf-8")
        content_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        payload = {"message": f"Add/Update {path}", "content": b64, "branch": head}
        if path in remote_map:
            payload["sha"] = remote_map[path]
        if dry_run:
            ops.append({"op": "add_or_update", "path": path, "payload": payload})
        else:
            resp = requests.put(content_url, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            ops.append({"op": "add_or_update", "path": path, "response": resp.json()})

    # Apply deletes
    for path in deletes:
        content_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        sha = remote_map.get(path)
        payload = {"message": f"Delete {path}", "branch": head, "sha": sha}
        if dry_run:
            ops.append({"op": "delete", "path": path, "payload": payload})
        else:
            resp = requests.delete(content_url, headers=headers, json=payload, timeout=timeout)
            # if file missing, ignore
            if resp.status_code not in (200, 204):
                resp.raise_for_status()
            ops.append({"op": "delete", "path": path, "response": resp.json() if resp.content else None})

    branch_url = f"https://github.com/{repo_full}/tree/{head}"
    return {"branch_url": branch_url, "operations": ops}
