"""
Hard denylist for run_command / open_application (project spec section
15: "Verhindere zumindest offensichtliche gefährliche Fehlbedienung").

This is defense-in-depth, not the primary safety mechanism - the
primary mechanism is that both tools are CONFIRM_REQUIRED, so a human
must approve every single invocation via the PWA before anything runs.
This denylist exists for the case a human might approve something
without reading it closely: a handful of unambiguously catastrophic
patterns (wiping a drive, a fork bomb, shutting the machine down) are
refused outright and never even reach the confirmation step.

This is intentionally NOT trying to be a complete sandbox or to catch
every possible harmful command - that's what the confirmation step and
ALLOWED_DIRECTORIES scoping (app/tools/paths.py) are for.
"""
from __future__ import annotations

import re

_BLOCKED_PATTERNS: list[tuple[str, str]] = [
    (r"rm\s+-rf\s+/(?:\s|$)", "recursive delete of the filesystem root"),
    (r"rm\s+-rf\s+~\s*(?:$|/\s*$)", "recursive delete of the home directory"),
    (r"format\s+[a-z]:", "formatting a drive"),
    (r"del\s+/s\s+/q\s+[a-z]:\\?\s*$", "recursive silent delete of a whole drive"),
    (r"mkfs(\.\w+)?\s", "creating a filesystem (wipes the target)"),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&?\s*\}\s*;\s*:", "a fork bomb"),
    (r"\bshutdown\b", "shutting down/restarting the machine"),
    (r"stop-computer|restart-computer", "shutting down/restarting the machine"),
    (r"reg\s+delete\s+hklm", "deleting a machine-wide registry hive"),
]


def is_blocked_command(command: str) -> str | None:
    """Returns a human-readable reason if `command` matches a hard-blocked
    pattern, else None."""
    lowered = command.lower()
    for pattern, reason in _BLOCKED_PATTERNS:
        if re.search(pattern, lowered):
            return reason
    return None
