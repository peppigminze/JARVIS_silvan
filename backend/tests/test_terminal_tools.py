from __future__ import annotations

import pytest

from app.config import get_settings
from app.database.db import Base, SessionLocal, engine
from app.database.models import CommandLog
from app.tools.terminal_tools import RunCommandTool


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOWED_DIRECTORIES", str(tmp_path))
    monkeypatch.setenv("TERMINAL_TIMEOUT_SECONDS", "5")
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


async def test_run_command_executes_and_logs(sandbox, db_session):
    result = await RunCommandTool().execute(db=db_session, command="echo hello-jarvis", working_directory=str(sandbox))
    assert result.success is True
    assert "hello-jarvis" in result.data["stdout"]
    assert result.data["exit_code"] == 0

    logs = db_session.query(CommandLog).all()
    assert len(logs) == 1
    assert logs[0].command == "echo hello-jarvis"
    assert logs[0].exit_code == 0


async def test_run_command_reports_nonzero_exit_code(sandbox, db_session):
    result = await RunCommandTool().execute(
        db=db_session, command="exit 3", working_directory=str(sandbox)
    )
    assert result.success is False
    assert result.data["exit_code"] == 3


async def test_run_command_blocked_pattern_never_executes(sandbox, db_session):
    result = await RunCommandTool().execute(
        db=db_session, command="rm -rf /", working_directory=str(sandbox)
    )
    assert result.success is False
    assert "Refused" in result.error
    # Never even ran, so nothing was logged.
    assert db_session.query(CommandLog).count() == 0


async def test_run_command_outside_allowed_directory_is_refused(sandbox, db_session, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    result = await RunCommandTool().execute(db=db_session, command="echo hi", working_directory=str(outside))
    assert result.success is False
    assert db_session.query(CommandLog).count() == 0


async def test_run_command_times_out(sandbox, db_session, monkeypatch):
    monkeypatch.setenv("TERMINAL_TIMEOUT_SECONDS", "0.2")
    get_settings.cache_clear()
    # `ping` with a huge count keeps running well past the timeout on Windows.
    result = await RunCommandTool().execute(
        db=db_session, command="ping -n 30 127.0.0.1", working_directory=str(sandbox)
    )
    assert result.success is False
    assert "timed out" in result.error

    logs = db_session.query(CommandLog).all()
    assert len(logs) == 1
    assert logs[0].timed_out is True
