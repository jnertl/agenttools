import os
import tempfile
from agenttools.tools import write_file, read_file


def test_write_file_plain_filename(tmp_path, monkeypatch):
    # Use a temporary cwd to avoid writing into project dir
    monkeypatch.chdir(tmp_path)
    fname = "notes.txt"
    res = write_file.invoke({"file_path": fname, "content": "hello world"})
    assert "Successfully wrote" in res
    assert (tmp_path / fname).read_text(encoding="utf-8") == "hello world"


def test_write_file_with_dir(tmp_path):
    dirp = tmp_path / "subdir"
    fname = str(dirp / "out.txt")
    res = write_file.invoke({"file_path": fname, "content": "content"})
    assert "Successfully wrote" in res
    assert dirp.joinpath("out.txt").read_text(encoding="utf-8") == "content"


def test_read_file_error(tmp_path):
    # non-existent file
    res = read_file.invoke({"file_path": str(tmp_path / "nope.txt")})
    assert "Error" in res
