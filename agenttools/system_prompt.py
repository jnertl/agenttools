"""System prompt loading utility.

Provides a helper to load a system prompt from a file and substitute
environment-variable placeholders in the form {{VARNAME}}.
"""

import os
import re
from typing import Match


def load_system_prompt() -> str:
    """Load the system prompt from the path specified in SYSTEM_PROMPT_FILE.

    The file may contain placeholders like {{VARNAME}} which are replaced by
    the corresponding environment variable. If SYSTEM_PROMPT_FILE is not set
    or the file can't be read, or a referenced env var is missing, a
    ValueError is raised.
    """
    env_path = os.getenv("SYSTEM_PROMPT_FILE")
    if not env_path:
        raise ValueError("SYSTEM_PROMPT_FILE environment variable was not set")

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        raise ValueError(f"SYSTEM_PROMPT_FILE is set to '{env_path}' but the file was not found")

    pattern = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

    def _replace(match: Match[str]) -> str:
        var = match.group(1)
        val = os.getenv(var)
        if val is None:
            raise ValueError(f"Environment variable '{var}' referenced in SYSTEM_PROMPT_FILE is not set")
        return val

    return pattern.sub(_replace, text)


__all__ = ["load_system_prompt"]
