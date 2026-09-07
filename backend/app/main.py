from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agent as agent_api
from app.api import health, memory, messages, sync, tasks
from app.config import get_settings
from app.database.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jarvis.backend")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("JARVIS backend starting (env=%s)", settings.APP_ENV)
    init_db()
    logger.info("Database ready.")
    yield


app = FastAPI(title="JARVIS Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(messages.router)
app.include_router(tasks.router)
app.include_router(memory.router)
app.include_router(sync.router)
app.include_router(agent_api.router)


@app.get("/")
def root() -> dict:
    return {"name": "JARVIS Backend", "status": "running"}
