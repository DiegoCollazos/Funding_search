"""Enriquecimiento de un resultado crudo de scraping en campos estructurados.

Deliberadamente sin ninguna dependencia de SQLAlchemy/FastAPI: esta función
la usan tanto el backend con base de datos (``runner.py``) como el script
de línea de comandos para la variante estática de GitHub Pages
(``scripts/run_scraping.py``), que no tiene (ni necesita) esas dependencias.
"""

from __future__ import annotations

import datetime as dt

from .extraction import (
    assess_university_eligibility,
    extract_amount,
    extract_deadline,
    extract_objective,
    parse_date_generic,
)
from .sdg_classifier import classify_sdg, extract_theme_keywords


def compute_status(deadline: dt.date | None) -> str:
    if deadline is None:
        return "Por confirmar"
    return "Vigente" if deadline >= dt.date.today() else "Cerrada"


def enrich_raw_call(raw: dict, scope: str) -> dict:
    """Convierte un diccionario crudo de un adaptador en los campos de una convocatoria."""
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
        "scope": scope,
        "sdg_list": ",".join(sdg_list),
        "theme_keywords": ",".join(keywords),
        "university_eligibility": eligibility,
        "university_eligibility_note": eligibility_note,
        "status": compute_status(deadline_parsed),
    }


__all__ = ["enrich_raw_call", "compute_status"]
