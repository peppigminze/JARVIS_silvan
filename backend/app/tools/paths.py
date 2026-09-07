"""
Filesystem sandboxing for PC tools (project spec sections 13, 16, 37).

Every file/terminal tool MUST resolve user/LLM-supplied paths through
resolve_allowed_path() before touching disk. It never trusts the raw
string: it resolves symlinks and ".." segments first (so a clever path
can't escape via traversal) and then checks the result is still inside
one of the operator-configured ALLOWED_DIRECTORIES. Nothing is
reachable at all until the user opts a directory in via .env.
"""
from __future__ import annotations

from pathlib import Path

from app.config import get_settings


class PathNotAllowedError(Exception):
    """Raised when a path is outside every configured allowed directory,
    or no allowed directories are configured at all."""


def allowed_roots() -> list[Path]:
    settings = get_settings()
    return [Path(d).resolve() for d in settings.allowed_directories_list]


def resolve_allowed_path(path_str: str) -> Path:
    roots = allowed_roots()
    if not roots:
        raise PathNotAllowedError(
            "No ALLOWED_DIRECTORIES configured - file/terminal tools are disabled "
            "until a directory is added in .env."
        )

    candidate = Path(path_str)
    if not candidate.is_absolute():
        # Relative paths resolve against the first allowed directory, not
        # the agent process's CWD - keeps behavior independent of where
        # the agent happens to be launched from.
        candidate = roots[0] / candidate

    resolved = candidate.resolve()
    for root in roots:
        if resolved == root or root in resolved.parents:
            return resolved
    raise PathNotAllowedError(f"Path '{resolved}' is outside the allowed directories.")
