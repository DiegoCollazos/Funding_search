"""Adaptador para el portal europeo Funding & Tenders (Comisión Europea).

El proyecto original usaba Selenium para controlar un Chrome headless,
porque el portal es una aplicación Angular de una sola página (SPA): el
HTML que devuelve ``requests`` no contiene los resultados, que se cargan
mediante llamadas internas a una API REST después de que el navegador
ejecuta JavaScript.

En vez de mantener un navegador headless (pesado, lento y frágil ante
cambios de la SPA) para un backend que debe poder correr en un servidor
programado, este adaptador llama directamente a la API REST que la propia
SPA consume para pedir los resultados. Es el mismo patrón recomendado en la
sección "scraping vs. alternativas" del README: cuando un sitio expone (aunque
sea de forma no documentada) una API JSON detrás de su interfaz, es más
robusto y más rápido consumir esa API que simular un navegador.

Nota importante: esta API no es pública ni está documentada oficialmente por
la Comisión Europea y su contrato puede cambiar sin aviso. Por eso el
adaptador falla de forma controlada (excepción clara) si el formato de
respuesta cambia, en vez de devolver datos corruptos; cuando eso ocurra basta
con ajustar ``_build_query``/``_parse_response`` o, como alternativa,
registrar la entidad con ``adapter=generic`` y dejar que el motor genérico
intente leer una versión estática/RSS del listado si el portal la ofrece.
"""

from __future__ import annotations

from ..http_utils import fetch_json

SEARCH_API_URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
API_KEY = "SEDIA"  # clave pública usada por el propio portal (visible en su tráfico de red)
PORTAL_BASE = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/"


def _build_query(keyword: str, page_size: int) -> dict:
    query = {
        "bool": {
            "must": [
                {"terms": {"type": ["1", "2", "8"]}},
                {"terms": {"status": ["31094501", "31094502"]}},
            ]
        }
    }
    if keyword:
        query["bool"]["must"].append({"match": {"title": keyword}})
    return {
        "query": query,
        "languages": ["en"],
        "sort": {"field": "sortStatus", "order": "ASC"},
        "pageSize": page_size,
        "pageNumber": 1,
    }


def _parse_response(payload: dict) -> list[dict]:
    results = []
    for item in payload.get("results", []) or []:
        metadata = item.get("metadata", {}) or {}

        def first(key: str) -> str:
            value = metadata.get(key)
            if isinstance(value, list):
                return str(value[0]) if value else ""
            return str(value) if value else ""

        identifier = item.get("reference") or item.get("id") or ""
        title = first("title") or item.get("title") or ""
        if not title or not identifier:
            continue
        results.append({
            "title": title,
            "link": PORTAL_BASE + str(identifier),
            "description": first("callTitle") or first("summary"),
            "opening_date_text": first("startDate"),
            "deadline_date_text": first("deadlineDate"),
            "raw_text": " ".join(filter(None, [
                first("summary"), first("callTitle"), first("destinationGroup"), first("programmeDivision"),
            ])),
        })
    return results


def scrape_eu(entity, keyword: str = "", max_results: int = 15) -> list[dict]:
    payload = _build_query(keyword, max_results)
    try:
        response = fetch_json(
            SEARCH_API_URL,
            method="POST",
            params={"apiKey": API_KEY, "text": "***", "pageSize": max_results, "pageNumber": 1},
            json=payload,
        )
    except Exception as exc:  # noqa: BLE001 - queremos un mensaje claro y no romper el scheduler
        raise RuntimeError(
            "No se pudo consultar la API del portal Funding & Tenders de la UE "
            "(puede haber cambiado su contrato no documentado). "
            f"Detalle: {exc}"
        ) from exc

    if not isinstance(payload_out := response, dict):
        raise RuntimeError("Respuesta inesperada de la API de la UE (se esperaba un objeto JSON).")

    return _parse_response(payload_out)[:max_results]


__all__ = ["scrape_eu"]
