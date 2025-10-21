import pytest

from agenttools.formatters import normalize_content


def test_string():
    assert normalize_content("hello") == "hello"


def test_dict_text():
    assert normalize_content({"type": "text", "text": "hi"}) == "hi"


def test_dict_content():
    assert normalize_content({"content": "ok"}) == "ok"


def test_list_and_nested():
    value = ["a", {"text": "b"}, ["c", {"content": "d"}], {"x": {"y": "z"}}]
    assert normalize_content(value) == "a b c d z"
