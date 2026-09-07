"""
Regression tests for the additive-column migration helper
(app/database/db.py::ensure_columns), used e.g. to add memory_type to
an existing memory_entries table without an Alembic setup. Must never
lose existing rows and must be safe to call repeatedly.
"""
from __future__ import annotations

from sqlalchemy import text

from app.database.db import ensure_columns, engine


def test_ensure_columns_adds_missing_column_without_losing_data():
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS widgets_test"))
        conn.execute(text("CREATE TABLE widgets_test (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"))
        conn.execute(text("INSERT INTO widgets_test (id, name) VALUES (1, 'existing-row')"))
        conn.commit()

    ensure_columns("widgets_test", {"kind": "VARCHAR(32) NOT NULL DEFAULT 'basic'"})

    with engine.connect() as conn:
        rows = list(conn.execute(text("SELECT id, name, kind FROM widgets_test")))
        conn.execute(text("DROP TABLE widgets_test"))
        conn.commit()

    assert rows == [(1, "existing-row", "basic")]


def test_ensure_columns_is_idempotent():
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS widgets_test2"))
        conn.execute(text("CREATE TABLE widgets_test2 (id INTEGER PRIMARY KEY)"))
        conn.commit()

    # Calling it twice must not raise (e.g. "duplicate column name").
    ensure_columns("widgets_test2", {"kind": "VARCHAR(32) NOT NULL DEFAULT 'basic'"})
    ensure_columns("widgets_test2", {"kind": "VARCHAR(32) NOT NULL DEFAULT 'basic'"})

    with engine.connect() as conn:
        columns = [row[1] for row in conn.execute(text("PRAGMA table_info(widgets_test2)"))]
        conn.execute(text("DROP TABLE widgets_test2"))
        conn.commit()

    assert columns.count("kind") == 1


def test_memory_entries_has_memory_type_column_after_init():
    """End-to-end: the real memory_entries table (created via
    Base.metadata.create_all before migrations existed, in spirit) must
    have memory_type after init_db() runs run_migrations()."""
    from app.database.db import init_db

    init_db()
    with engine.connect() as conn:
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(memory_entries)"))}
    assert "memory_type" in columns
