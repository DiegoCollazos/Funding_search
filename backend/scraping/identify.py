"""Lógica para la herramienta de identificación rápida de una convocatoria puntual.

A diferencia del flujo de entidades (que scrapea listados completos), aquí el
usuario pega la URL (o el texto) de UNA convocatoria específica y el sistema
aplica las mismas heurísticas de extracción para responder de inmediato: si
es nacional o internacional, cuál es su objetivo, fecha de cierre, monto y
viabilidad de participación de una universidad pública.
"""

from __future__ import annotations

from .extraction import assess_university_eligibility, extract_amount, extract_deadline, extract_objective
from .http_utils import fetch_page, parse_html, visible_text
from .scope_classifier import classify_scope
from .sdg_classifier import classify_sdg


def identify_call(url: str = "", text: str = "") -> dict:
    page_text = text or ""
    title = ""

    if url and not page_text:
        html = fetch_page(url)
        soup = parse_html(html)
        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text(" ", strip=True) if title_tag else ""
        page_text = visible_text(soup, limit=12000)

    if not title:
        first_line = page_text.strip().splitlines()[0] if page_text.strip() else ""
        title = first_line[:200]

    scope, scope_confidence = classify_scope(url=url, text=page_text)
    deadline_text = extract_deadline(page_text)
    amount_text, _amount_value, amount_currency = extract_amount(page_text)
    if amount_text and amount_currency and amount_currency.upper() not in amount_text.upper():
        amount_text = f"{amount_text} {amount_currency}"
    objective = extract_objective(page_text, title)
    eligibility, eligibility_note = assess_university_eligibility(page_text)
    sdg_list = classify_sdg(page_text)

    return {
        "scope": scope,
        "scope_confidence": scope_confidence,
        "title": title,
        "objective": objective,
        "deadline_date_text": deadline_text,
        "amount_text": amount_text,
        "university_eligibility": eligibility,
        "university_eligibility_note": eligibility_note,
        "sdg_list": sdg_list,
        "raw_excerpt": page_text[:800],
    }


__all__ = ["identify_call"]
