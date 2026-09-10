"""Orquestador de scraping: ejecuta el adaptador de una entidad, enriquece
los resultados crudos con las heurísticas de extracción/clasificación, y
sincroniza todo en la base de datos (alta de convocatorias nuevas,
actualización de las existentes, marcado de cerradas, bitácora)."""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from .. import models
from .adapters.registry import get_adapter
from .extraction import (
    assess_university_eligibility,
    extract_amount,
    extract_deadline,
    extract_objective,
    parse_date_generic,
)
from .sdg_classifier import classify_sdg, extract_theme_keywords


def _compute_status(deadline: dt.date | None) -> str:
    if deadline is None:
        return "Por confirmar"
    return "Vigente" if deadline >= dt.date.today() else "Cerrada"


def enrich_raw_call(raw: dict, entity: models.Entity) -> dict:
    """Convierte un diccionario crudo de un adaptador en los campos del modelo Call."""
    raw_text = raw.get("raw_text") or raw.get("description") or ""
    title = (raw.get("title") or "").strip()

    deadline_text = raw.get("deadline_date_text") or extract_deadline(raw_text)
    deadline_parsed = parse_date_generic(deadline_text)

    amount_text, amount_value, amount_currency = extract_amount(raw_text)
    objective = extract_objective(raw_text, title)
    eligibility, eligibility_note = assess_university_eligibility(raw_text)
    sdg_list = classify_sdg(raw_text or title)
    keywords = extract_theme_keywords(raw_text or title)

    return {
        "title": title or "(sin título)",
        "link": raw.get("link") or "",
        "objective": objective,
        "description": (raw_text or "")[:4000],
        "opening_date_text": raw.get("opening_date_text") or "",
        "deadline_date_text": deadline_text,
        "deadline_date": deadline_parsed,
        "amount_text": amount_text,
        "amount_value": amount_value,
        "amount_currency": amount_currency,
        "scope": entity.scope,
        "sdg_list": ",".join(sdg_list),
        "theme_keywords": ",".join(keywords),
        "university_eligibility": eligibility,
        "university_eligibility_note": eligibility_note,
        "status": _compute_status(deadline_parsed),
    }


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
            enriched = enrich_raw_call(raw, entity)

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


__all__ = ["run_scrape_for_entity", "enrich_raw_call"]
