"""Programador de scraping en segundo plano.

En vez de que el usuario tenga que ejecutar manualmente un script por cada
entidad (como en la versión de escritorio original), este módulo revisa
periódicamente el banco de entidades y dispara el scraping de las que ya
cumplieron su frecuencia configurada (diaria, semanal o mensual). Esto es lo
que permite el requisito de "programar el scraping" al agregar una entidad:
basta con elegir la frecuencia en el formulario del banco de entidades.
"""

from __future__ import annotations

import datetime as dt
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import sessionmaker

from . import models
from .scraping.runner import run_scrape_for_entity

logger = logging.getLogger("funding_search.scheduler")

_FREQUENCY_DELTAS = {
    "diario": dt.timedelta(days=1),
    "semanal": dt.timedelta(weeks=1),
    "mensual": dt.timedelta(days=30),
}

# Cada cuántos minutos el scheduler revisa si alguna entidad ya está "vencida"
# según su frecuencia configurada. No es la frecuencia de scraping en sí.
_TICK_MINUTES = 30

_scheduler: BackgroundScheduler | None = None


def _is_due(entity: models.Entity, now: dt.datetime) -> bool:
    if not entity.active or entity.schedule_frequency == "manual":
        return False
    if entity.last_scraped_at is None:
        return True
    delta = _FREQUENCY_DELTAS.get(entity.schedule_frequency)
    if delta is None:
        return False
    return now - entity.last_scraped_at >= delta


def _tick(session_factory: sessionmaker) -> None:
    db = session_factory()
    try:
        now = dt.datetime.utcnow()
        entities = db.query(models.Entity).filter(models.Entity.active.is_(True)).all()
        for entity in entities:
            if _is_due(entity, now):
                logger.info("Scraping programado: %s", entity.name)
                try:
                    run_scrape_for_entity(db, entity)
                except Exception:  # noqa: BLE001 - no debe tumbar el scheduler completo
                    logger.exception("Fallo al scrapear %s", entity.name)
    finally:
        db.close()


def start_scheduler(session_factory: sessionmaker) -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _tick,
        "interval",
        minutes=_TICK_MINUTES,
        args=[session_factory],
        id="funding_search_scrape_tick",
        next_run_time=dt.datetime.utcnow() + dt.timedelta(seconds=15),
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Scheduler de scraping iniciado (revisión cada %s minutos).", _TICK_MINUTES)
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


__all__ = ["start_scheduler", "stop_scheduler"]
