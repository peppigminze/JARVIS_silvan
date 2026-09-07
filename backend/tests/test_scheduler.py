"""
Tests for the reminder scheduler (app/scheduler.py). Uses the app's
real engine/session_scope directly (like test_agent_pipeline.py) since
check_due_reminders() is a plain synchronous function, not reachable
through the TestClient's isolated per-test database.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.database.db import Base, SessionLocal, engine, session_scope
from app.database.models import Task, TaskPriority, TaskStatus, advance_due_date
from app.scheduler import check_due_reminders


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _make_task(db_session, **overrides) -> Task:
    defaults = dict(
        title="Test-Reminder",
        priority=TaskPriority.medium,
        status=TaskStatus.pending,
        reminder_enabled=True,
        recurrence="none",
    )
    defaults.update(overrides)
    task = Task(**defaults)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def test_due_one_off_reminder_fires_once(db_session):
    task = _make_task(db_session, due_at=datetime.now(timezone.utc) - timedelta(minutes=1))

    fired = check_due_reminders()
    assert fired == 1

    db_session.refresh(task)
    assert task.last_notified_at is not None

    # Second tick: already notified for this occurrence, must not fire again.
    fired_again = check_due_reminders()
    assert fired_again == 0


def test_future_reminder_does_not_fire(db_session):
    _make_task(db_session, due_at=datetime.now(timezone.utc) + timedelta(hours=1))
    assert check_due_reminders() == 0


def test_disabled_reminder_does_not_fire(db_session):
    _make_task(
        db_session,
        due_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        reminder_enabled=False,
    )
    assert check_due_reminders() == 0


def test_completed_task_reminder_does_not_fire(db_session):
    _make_task(
        db_session,
        due_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        status=TaskStatus.completed,
    )
    assert check_due_reminders() == 0


def test_recurring_reminder_reschedules_instead_of_disappearing(db_session):
    original_due = datetime.now(timezone.utc) - timedelta(minutes=1)
    task = _make_task(db_session, due_at=original_due, recurrence="daily")

    assert check_due_reminders() == 1
    db_session.refresh(task)

    assert task.status == TaskStatus.pending  # recurring reminders don't auto-complete
    new_due = task.due_at.replace(tzinfo=timezone.utc)  # SQLite round-trip drops tzinfo
    assert new_due > original_due
    assert (new_due - original_due) >= timedelta(hours=23)  # ~1 day forward


def test_missed_reminder_while_offline_fires_on_next_tick(db_session):
    """Simulates the PC having been off for 3 days: due_at is far in the
    past, but the very next scheduler tick after 'restart' must still
    fire it exactly once, not lose it (project spec section 12)."""
    long_overdue = datetime.now(timezone.utc) - timedelta(days=3)
    task = _make_task(db_session, due_at=long_overdue)

    assert check_due_reminders() == 1
    db_session.refresh(task)
    assert task.last_notified_at is not None


def test_advance_due_date_daily_and_weekly():
    base = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    assert advance_due_date(base, "daily") == datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)
    assert advance_due_date(base, "weekly") == datetime(2026, 1, 8, 9, 0, tzinfo=timezone.utc)


def test_advance_due_date_monthly_handles_month_end_clamping():
    jan31 = datetime(2026, 1, 31, 9, 0, tzinfo=timezone.utc)
    # 2026 is not a leap year - Feb has 28 days.
    assert advance_due_date(jan31, "monthly") == datetime(2026, 2, 28, 9, 0, tzinfo=timezone.utc)


def test_advance_due_date_monthly_wraps_year():
    dec = datetime(2026, 12, 15, 9, 0, tzinfo=timezone.utc)
    assert advance_due_date(dec, "monthly") == datetime(2027, 1, 15, 9, 0, tzinfo=timezone.utc)


def test_advance_due_date_rejects_unknown_recurrence():
    with pytest.raises(ValueError):
        advance_due_date(datetime.now(timezone.utc), "hourly")
