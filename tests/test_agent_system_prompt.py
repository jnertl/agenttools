import os
import tempfile
import pytest
from agenttools.agent import FileAgent


def test_system_prompt_file_substitution(tmp_path, monkeypatch):
    f = tmp_path / "sys_prompt.txt"
    f.write_text("You must follow {{REQ}}", encoding="utf-8")

    monkeypatch.setenv("SYSTEM_PROMPT_FILE", str(f))
    monkeypatch.setenv("REQ", "requirements.txt")

    # Should not raise
    agent = FileAgent(provider="ollama")
    # The system prompt is used internally; at least FileAgent was created
    assert agent is not None


def test_system_prompt_file_missing_env(tmp_path, monkeypatch):
    f = tmp_path / "sys_prompt2.txt"
    f.write_text("Use {{MISSING_VAR}}", encoding="utf-8")

    monkeypatch.setenv("SYSTEM_PROMPT_FILE", str(f))
    # Ensure MISSING_VAR is not set
    if "MISSING_VAR" in os.environ:
        monkeypatch.delenv("MISSING_VAR", raising=False)

    with pytest.raises(ValueError):
        FileAgent(provider="ollama")
