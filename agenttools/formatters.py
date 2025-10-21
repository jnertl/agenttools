"""Response formatting helpers for agenttools.

This module provides helpers to normalize various LLM/agent response
shapes into plain human-readable strings.
"""

from typing import Any


def normalize_content(content: Any) -> str:
    """Normalize various message content shapes into a human-readable string.

    Handles:
    - plain strings
    - numbers
    - dicts like {'type': 'text', 'text': '...'} or {'content': '...'}
    - lists/tuples of the above
    - nested structures
    """
    if content is None:
        return ""

    # Strings and simple scalars
    if isinstance(content, str):
        return content
    if isinstance(content, (int, float, bool)):
        return str(content)

    # Dicts: try common keys first
    if isinstance(content, dict):
        for key in ("text", "content", "message", "body", "answer"):
            if key in content:
                return normalize_content(content[key])

        # Some providers use {'type': 'text', 'text': '...'}
        if content.get("type") in ("text", "message") and "text" in content:
            return normalize_content(content["text"])

        # Fallback: collect and join any stringifiable values
        parts = []
        for v in content.values():
            t = normalize_content(v)
            if t:
                parts.append(t)
        return " ".join(parts)

    # Lists / tuples: join normalized parts with spaces
    if isinstance(content, (list, tuple)):
        parts = []
        for item in content:
            t = normalize_content(item)
            if t:
                parts.append(t)
        return " ".join(parts)

    # Fallback to string conversion
    try:
        return str(content)
    except Exception:
        return ""


__all__ = ["normalize_content"]
