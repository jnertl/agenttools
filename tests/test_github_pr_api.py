import os
import json
import subprocess
from pathlib import Path

import pytest

from agenttools.github_pr import push_branch_via_api, push_tree_via_api


class DummyResp:
    def __init__(self, status_code=200, json_data=None, text="ok", content=b""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text
        self.content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("http error")

    def json(self):
        return self._json


def test_push_branch_via_api_name_status(monkeypatch, tmp_path):
    # prepare local files
    git_dir = str(tmp_path)
    (tmp_path / "new.txt").write_text("new content")
    (tmp_path / "existing.txt").write_text("updated content")

    # fake subprocess.run for git diff --name-status
    def fake_run(cmd, check, stdout, stderr):
        if cmd[:4] == ["git", "-C", git_dir, "diff"]:
            out = b"A\tnew.txt\nM\texisting.txt\nD\told.txt\n"
            return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr=b"")
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr("subprocess.run", fake_run)

    calls = {"gets": [], "puts": [], "deletes": [], "posts": []}

    def fake_get(url, headers=None, params=None, timeout=None):
        calls["gets"].append((url, params))
        # content lookup for existing.txt and old.txt
        if url.endswith("/contents/existing.txt"):
            return DummyResp(200, json_data={"sha": "existingsha"})
        if url.endswith("/contents/old.txt"):
            return DummyResp(200, json_data={"sha": "oldsha"})
        # base ref
        if "/git/ref/heads/" in url:
            return DummyResp(200, json_data={"object": {"sha": "basecommitsha"}})
        # head ref get -> not found
        if "/git/ref/heads/issue" in url:
            return DummyResp(404, json_data={})
        return DummyResp(404, json_data={})

    def fake_put(url, headers=None, json=None, timeout=None):
        calls["puts"].append((url, json))
        return DummyResp(201, json_data={"content": {"path": json.get("message")}})

    def fake_delete(url, headers=None, json=None, timeout=None):
        calls["deletes"].append((url, json))
        return DummyResp(200, json_data={"commit": {"message": json.get("message")}})

    def fake_post(url, headers=None, json=None, timeout=None):
        calls["posts"].append((url, json))
        return DummyResp(201, json_data={})

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("requests.put", fake_put)
    monkeypatch.setattr("requests.delete", fake_delete)
    monkeypatch.setattr("requests.post", fake_post)

    res = push_branch_via_api(git_dir, "owner/repo", base="main", head="issue_1", token="fake-token")
    assert "branch_url" in res
    ops = res.get("operations")
    # Expect at least three ops: add_or_update new, add_or_update existing, delete old
    op_types = [o.get("op") for o in ops]
    assert "add_or_update" in op_types
    assert "delete" in op_types


def test_push_tree_via_api_dry_run(monkeypatch, tmp_path):
    # Create local tree
    git_dir = str(tmp_path)
    (tmp_path / "a.txt").write_text("A")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("B")

    # fake remote tree: only has c.txt
    base_commit_sha = "basecommit"
    base_tree_sha = "basetree"

    def fake_get(url, headers=None, params=None, timeout=None):
        if url.endswith("/git/ref/heads/main"):
            return DummyResp(200, json_data={"object": {"sha": base_commit_sha}})
        if "/git/commits/" in url:
            return DummyResp(200, json_data={"tree": {"sha": base_tree_sha}})
        if "/git/trees/" in url:
            # remote has only c.txt
            return DummyResp(200, json_data={"tree": [{"path": "c.txt", "type": "blob", "sha": "csha"}]})
        return DummyResp(404, json_data={})

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr("requests.get", fake_get)

    res = push_tree_via_api(git_dir, "owner/repo", base="main", head="newbranch", token="fake-token", dry_run=True)
    assert "branch_url" in res
    ops = res.get("operations")
    # In dry-run we should see planned add_or_update for a.txt and sub/b.txt and delete for c.txt
    op_summary = {o.get("op"): o for o in ops}
    assert any(o.get("op") == "add_or_update" for o in ops)
    assert any(o.get("op") == "delete" for o in ops)