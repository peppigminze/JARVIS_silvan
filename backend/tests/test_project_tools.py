from __future__ import annotations

import pytest

from app.database.db import Base, SessionLocal, engine
from app.database.models import Project
from app.tools.project_tools import ListProjectsTool


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


async def test_list_projects_empty(db_session):
    result = await ListProjectsTool().execute(db=db_session)
    assert result.success is True
    assert result.data == []


async def test_list_projects_returns_registered_projects(db_session):
    project = Project(name="JARVIS", path="C:\\JARVIS", description="Assistant")
    project.technologies = ["Python", "React"]
    db_session.add(project)
    db_session.commit()

    result = await ListProjectsTool().execute(db=db_session)

    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0]["name"] == "JARVIS"
    assert result.data[0]["technologies"] == ["Python", "React"]


async def test_list_projects_filters_by_name(db_session):
    for name in ("JARVIS", "AlwaysMC"):
        db_session.add(Project(name=name))
    db_session.commit()

    result = await ListProjectsTool().execute(db=db_session, name="jarvis")

    assert len(result.data) == 1
    assert result.data[0]["name"] == "JARVIS"
