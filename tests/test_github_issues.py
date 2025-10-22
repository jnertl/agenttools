import json
import pytest

from agenttools.github_issues import send_issue_comment


def test_compose_and_dry_run():
    out = send_issue_comment(
        repo_full_name="owner/repo",
        issue_number=42,
        title="Bug: fail",
        body="Steps to reproduce...",
        action="investigate",
        issue_url="https://github.com/owner/repo/issues/42",
        dry_run=True,
    )

    assert out["url"] is None
    assert "body" in out["payload"]
    assert "investigate" in out["payload"]["body"]


class DummyResp:
    def __init__(self, status_code=201, json_data=None, text="ok"):
        self.status_code = status_code
        self._json = json_data or {"html_url": "https://github.com/owner/repo/issues/42#issuecomment-1"}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("http error")

    def json(self):
        return self._json


def test_post_comment_success(monkeypatch):
    called = {}

    def fake_post(url, headers=None, data=None, timeout=None):
        called['url'] = url
        called['headers'] = headers
        called['data'] = data
        return DummyResp()

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr("requests.post", fake_post)

    res = send_issue_comment("owner/repo", 42, title="t", body="b", action="a", issue_url="u")
    assert res["url"].startswith("https://github.com/")
    assert 'owner/repo/issues/42/comments' in called['url']
    payload = json.loads(called['data'])
    assert "Action" in payload["body"]


def test_post_comment_http_error(monkeypatch):
    def fake_post(url, headers=None, data=None, timeout=None):
        return DummyResp(status_code=500, json_data={"message": "server error"}, text="server error")

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr("requests.post", fake_post)

    with pytest.raises(Exception):
        send_issue_comment("owner/repo", 1, body="b")
