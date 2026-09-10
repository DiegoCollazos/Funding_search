"""Punto de entrada de la aplicación: API REST + servidor de la herramienta HTML."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import SessionLocal, init_db
from .routers import calls, entities, identify, stats
from .scheduler import start_scheduler, stop_scheduler
from .seed_data import run_seed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()
    start_scheduler(SessionLocal)
    yield
    stop_scheduler()


app = FastAPI(
    title="Funding Search",
    description="Plataforma para la identificación de oportunidades de financiación (nacionales e internacionales).",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(entities.router)
app.include_router(calls.router)
app.include_router(identify.router)
app.include_router(stats.router)

if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
