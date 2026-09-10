"""Orquestador de scraping (variante con base de datos): ejecuta el adaptador
de una entidad, enriquece los resultados crudos con ``enrich.enrich_raw_call``
y sincroniza todo en la base de datos (alta de convocatorias nuevas,
actualización de las existentes, marcado de cerradas, bitácora).

Para la variante estática publicada en GitHub Pages, ver
``scripts/run_scraping.py``, que reutiliza el mismo ``enrich_raw_call`` pero
persiste en archivos JSON en vez de en esta base de datos.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from .. import models
from .adapters.registry import get_adapter
from .enrich import enrich_raw_call

__all__ = ["run_scrape_for_entity", "enrich_raw_call"]


def run_scrape_for_entity(db: Session, entity: models.Entity) -> models.ScrapeLog:
    log = models.ScrapeLog(entity_id=entity.id, started_at=dt.datetime.utcnow())
    db.add(log)

    calls_found = 0
    calls_new = 0
    try:
        adapter = get_adapter(entity.adapter)
        raw_calls = adapter(entity) or []
        calls_found = len(raw_calls)

        for raw in raw_calls:
            if not raw.get("link") or not raw.get("title"):
                continue
            enriched = enrich_raw_call(raw, entity.scope)

            existing = (
                db.query(models.Call)
                .filter(models.Call.entity_id == entity.id, models.Call.link == enriched["link"])
                .first()
            )
            now = dt.datetime.utcnow()
            if existing:
                for key, value in enriched.items():
                    setattr(existing, key, value)
                existing.last_seen_at = now
            else:
                new_call = models.Call(entity_id=entity.id, first_seen_at=now, last_seen_at=now, **enriched)
                db.add(new_call)
                calls_new += 1

        entity.last_status = "ok"
        entity.last_message = f"{calls_found} convocatoria(s) encontradas, {calls_new} nueva(s)."
        log.status = "ok"
        log.message = entity.last_message
    except Exception as exc:  # noqa: BLE001 - se registra el error para diagnosticarlo desde la UI
        entity.last_status = "error"
        entity.last_message = str(exc)
        log.status = "error"
        log.message = str(exc)
    finally:
        entity.last_scraped_at = dt.datetime.utcnow()
        log.finished_at = dt.datetime.utcnow()
        log.calls_found = calls_found
        log.calls_new = calls_new
        db.commit()

    return log
