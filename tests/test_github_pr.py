import subprocess
import json
import pytest

from agenttools.github_pr import (
    parse_repo_full_name,
    get_git_diff,
    create_pull_request,
)


def test_parse_repo_full_name_variants():
    assert parse_repo_full_name("owner/repo") == "owner/repo"
    assert parse_repo_full_name("https://github.com/owner/repo.git") == "owner/repo"
    assert parse_repo_full_name("git@github.com:owner/repo.git") == "owner/repo"
    with pytest.raises(ValueError):
        parse_repo_full_name("not-a-valid-url")


def test_get_git_diff_success(monkeypatch, tmp_path):
    git_dir = str(tmp_path)

    def fake_run(cmd, check, stdout, stderr):
        # emulate `git -C <dir> fetch --all`
        if cmd[:4] == ["git", "-C", git_dir, "fetch"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

        # emulate `git -C <dir> diff ...`
        if cmd[:4] == ["git", "-C", git_dir, "diff"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=b"sample-diff-content", stderr=b"")

        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr("subprocess.run", fake_run)

    diff = get_git_diff(git_dir, "main", "feature/1")
    assert "sample-diff-content" in diff


def test_get_git_diff_truncation(monkeypatch, tmp_path):
    git_dir = str(tmp_path)

    big = b"A" * 300_000

    def fake_run(cmd, check, stdout, stderr):
        if cmd[:4] == ["git", "-C", git_dir, "fetch"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")
        if cmd[:4] == ["git", "-C", git_dir, "diff"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=big, stderr=b"")
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr("subprocess.run", fake_run)

    diff = get_git_diff(git_dir, "main", "feature/large", max_bytes=100_000)
    assert "Diff truncated" in diff


class DummyResp:
    def __init__(self, status_code=201, json_data=None, text="ok"):
        self.status_code = status_code
        self._json = json_data or {"html_url": "https://github.com/owner/repo/pull/1"}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("http error")

    def json(self):
        return self._json


def test_create_pull_request_success(monkeypatch):
    called = {}

    def fake_post(url, headers=None, data=None, timeout=None):
        called['url'] = url
        called['headers'] = headers
        called['data'] = data
        return DummyResp()

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr("requests.post", fake_post)

    res = create_pull_request("owner/repo", head="issue_1", base="main", title="T", body="B")
    assert res["url"].startswith("https://github.com/")
    assert 'owner/repo/pulls' in called['url']
    payload = json.loads(called['data'])
    assert payload["head"] == "issue_1"


def test_create_pull_request_http_error(monkeypatch):
    def fake_post(url, headers=None, data=None, timeout=None):
        return DummyResp(status_code=500, json_data={"message": "server error"}, text="server error")

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr("requests.post", fake_post)

    import requests as _requests

    with pytest.raises(_requests.HTTPError):
        create_pull_request("owner/repo", head="issue_1", base="main", title="T")


def test_create_pr_from_git_no_changes(monkeypatch, tmp_path):
    git_dir = str(tmp_path)
    # monkeypatch get_git_diff to return empty (accept kwargs like use_remote)
    monkeypatch.setattr("agenttools.github_pr.get_git_diff", lambda *args, **kwargs: "")

    res = __import__("agenttools.github_pr", fromlist=["create_pr_from_git"]).create_pr_from_git(
        git_dir=git_dir, repo_url="owner/repo", base="main", head="issue_1", dry_run=True
    )
    assert isinstance(res, str)
    assert "No changes" in res
