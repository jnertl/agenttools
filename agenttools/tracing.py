"""Simple tracing utility: prints to console and appends to a log file.

Provides trace_print which mirrors the built-in print signature for
convenience but also writes the output to `agent_log.txt` in the current
working directory.
"""

from __future__ import annotations

import os
import pprint
from typing import Any
from datetime import datetime, timezone

# Log file name used by trace_print
AGENT_LOG_FILE = "agent_log.txt"
_SILENT = False


def set_silent(silent: bool) -> None:
    """Set tracer silent mode.

    When silent is True, trace_print will only append to the log file and
    will not print to stdout.
    """
    global _SILENT
    _SILENT = bool(silent)


def trace_print(*args: Any, sep: str = " ", end: str = "\n", flush: bool = False, log_only: bool = False) -> None:
    # Format message like built-in print
    message = sep.join(str(a) for a in args) + end

    # Print to console unless silent mode is active
    if not _SILENT and not log_only:
        print(*args, sep=sep, end=end, flush=flush)

    # Append to log file with timestamp
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        # Normalize UTC ISO format to include a trailing Z instead of +00:00
        if timestamp.endswith("+00:00"):
            timestamp = timestamp[:-6] + "Z"
        log_line = f"[{timestamp}] {message}"
        log_path = os.path.join(os.getcwd(), AGENT_LOG_FILE)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception:
        # Never raise from the tracer; logging should be best-effort.
        pass

def log_response(response: any) -> None:
    # Debug: print structure when result is a dict (or show repr otherwise)
    try:
        if isinstance(response, dict):
            trace_print(f"Result is dict with keys: {list(response.keys())}", log_only=True)
            trace_print("Result (pprint):", log_only=True)
            trace_print(pprint.pformat(response), log_only=True)
        else:
            trace_print(f"Result type: {type(response)}", log_only=True)
            trace_print(repr(response), log_only=True)
    except Exception as dbg_err:
        trace_print(f"Failed to print result structure: {dbg_err}", log_only=True)

__all__ = ["trace_print"]
