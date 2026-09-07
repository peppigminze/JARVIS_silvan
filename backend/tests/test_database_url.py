"""
Regression test for the split-brain SQLite bug: the backend (started
from backend/) and the local PC agent (started from the project root,
see agent/run_agent.py) must resolve a relative DATABASE_URL to the
*same* file, otherwise data written by agent tool calls (create_task,
save_memory, ...) never shows up through the backend's API - see
app/database/db.py:_resolve_database_url for the full explanation.
"""
from __future__ import annotations

from pathlib import Path

from app.database.db import _BACKEND_DIR, _resolve_database_url


def test_relative_sqlite_url_resolves_against_backend_dir():
    resolved = _resolve_database_url("sqlite:///./jarvis.db")
    expected = (_BACKEND_DIR / "jarvis.db").resolve().as_posix()
    assert resolved == f"sqlite:///{expected}"


def test_resolution_is_independent_of_process_cwd(monkeypatch, tmp_path):
    # Simulate the agent's CWD (project root) differing from the
    # backend's CWD (backend/) - the resolved path must not change.
    monkeypatch.chdir(tmp_path)
    resolved = _resolve_database_url("sqlite:///./jarvis.db")
    expected = (_BACKEND_DIR / "jarvis.db").resolve().as_posix()
    assert resolved == f"sqlite:///{expected}"


def test_in_memory_url_is_left_untouched():
    assert _resolve_database_url("sqlite:///:memory:") == "sqlite:///:memory:"


def test_absolute_sqlite_url_is_left_untouched():
    absolute = Path("C:/some/absolute/path.db").as_posix()
    raw = f"sqlite:///{absolute}"
    assert _resolve_database_url(raw) == raw


def test_non_sqlite_url_is_left_untouched():
    raw = "postgresql://user:pass@localhost/jarvis"
    assert _resolve_database_url(raw) == raw
