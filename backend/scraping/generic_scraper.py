"""Motor de scraping genérico y configurable.

Este es el corazón de la mejora frente al proyecto original: en vez de tener
que escribir un script de Python por cada entidad nueva, el administrador
simplemente registra una URL en el banco de entidades. El motor intenta
"autodescubrir" el listado de convocatorias de la página (buscando el
contenedor con más enlaces que parezcan ítems de una lista) y, si el
administrador conoce la estructura HTML del sitio, puede afinar el resultado
guardando selectores CSS opcionales en ``Entity.scraper_config``:

    {
      "list_selector": "table tbody tr",
      "title_selector": "a",
      "link_selector": "a",
      "link_attr": "href",
      "description_selector": "td:nth-child(3)",
      "date_open_selector": "td:nth-child(4)",
      "date_close_selector": "td:nth-child(5)",
      "base_url": "https://ejemplo.gov.co",
      "follow_detail": true,
      "max_items": 15
    }

Todas las claves son opcionales. Cuando faltan selectores, se usa
autodescubrimiento heurístico. Este enfoque es deliberadamente más robusto
que depender de Selenium/scripts fijos por sitio: la mayoría de portales de
convocatorias (ministerios, fundaciones, cooperación) publican listados en
HTML estático, así que requests + BeautifulSoup basta, y cuando la
estructura de un sitio cambia, se corrige ajustando la configuración desde
la interfaz en vez de reescribir código.
"""

from __future__ import annotations

import json
from urllib.parse import urljoin

from .http_utils import fetch_page, parse_html, visible_text

_CONTAINER_CANDIDATES = [
    "table tbody tr",
    ".views-row",
    ".result-item",
    ".search-result",
    ".list-item",
    ".convocatoria",
    ".card",
    "article",
    "ul li",
]

_SKIP_HREF_PREFIXES = ("#", "javascript:", "mailto:", "tel:")


def _autodiscover(soup, base_url: str, max_items: int) -> list[dict]:
    best_matches: list[tuple[object, object, str]] = []
    for selector in _CONTAINER_CANDIDATES:
        items = soup.select(selector)
        matches = []
        for item in items:
            a = item.find("a", href=True)
            if not a:
                continue
            text = a.get_text(" ", strip=True)
            if 12 <= len(text) <= 250:
                matches.append((item, a, text))
        if len(matches) >= 3:
            best_matches = matches
            break
    if not best_matches:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().startswith(_SKIP_HREF_PREFIXES):
                continue
            text = a.get_text(" ", strip=True)
            if 15 <= len(text) <= 250:
                best_matches.append((a.parent, a, text))

    candidates: list[dict] = []
    seen_links: set[str] = set()
    for item, a, text in best_matches:
        href = a["href"]
        if href.lower().startswith(_SKIP_HREF_PREFIXES):
            continue
        link = urljoin(base_url, href)
        if link in seen_links:
            continue
        seen_links.add(link)
        candidates.append({
            "title": text,
            "link": link,
            "description": "",
            "opening_date_text": "",
            "deadline_date_text": "",
        })
        if len(candidates) >= max_items:
            break
    return candidates


def _configured_extract(soup, base_url: str, config: dict, max_items: int) -> list[dict]:
    items = soup.select(config["list_selector"])
    link_attr = config.get("link_attr", "href")
    candidates: list[dict] = []
    for item in items[:max_items]:
        title_el = item.select_one(config["title_selector"]) if config.get("title_selector") else item.find("a")
        link_el = item.select_one(config["link_selector"]) if config.get("link_selector") else item.find("a")
        if not title_el or not link_el or not link_el.get(link_attr):
            continue
        title = title_el.get_text(" ", strip=True)
        link = urljoin(base_url, link_el.get(link_attr))
        description = ""
        if config.get("description_selector"):
            desc_el = item.select_one(config["description_selector"])
            description = desc_el.get_text(" ", strip=True) if desc_el else ""
        opening = ""
        if config.get("date_open_selector"):
            open_el = item.select_one(config["date_open_selector"])
            opening = open_el.get_text(" ", strip=True) if open_el else ""
        deadline = ""
        if config.get("date_close_selector"):
            close_el = item.select_one(config["date_close_selector"])
            deadline = close_el.get_text(" ", strip=True) if close_el else ""
        candidates.append({
            "title": title,
            "link": link,
            "description": description,
            "opening_date_text": opening,
            "deadline_date_text": deadline,
        })
    return candidates


def scrape_entity_generic(entity) -> list[dict]:
    """Scrapea una entidad usando su URL y configuración opcional de selectores.

    Devuelve una lista de diccionarios crudos con al menos ``title`` y
    ``link``; los demás campos (fechas, monto, objetivo, ODS, elegibilidad)
    se completan después en ``runner.py`` a partir del texto de la página
    de detalle mediante heurísticas de extracción.
    """
    try:
        config = json.loads(entity.scraper_config or "{}")
    except (json.JSONDecodeError, TypeError):
        config = {}

    html = fetch_page(entity.url)
    soup = parse_html(html)
    base_url = config.get("base_url") or entity.url
    max_items = int(config.get("max_items", 15))

    if config.get("list_selector"):
        candidates = _configured_extract(soup, base_url, config, max_items)
    else:
        candidates = _autodiscover(soup, base_url, max_items)

    follow_detail = config.get("follow_detail", True)
    results: list[dict] = []
    for c in candidates:
        raw_text = c.get("description", "")
        if follow_detail and c.get("link"):
            try:
                detail_html = fetch_page(c["link"])
                detail_soup = parse_html(detail_html)
                detail_text = visible_text(detail_soup, limit=10000)
                if detail_text:
                    raw_text = detail_text
            except Exception:
                # Si la página de detalle falla, seguimos con lo que ya tengamos
                # (título + descripción del listado, si la hubo).
                pass
        c["raw_text"] = raw_text
        results.append(c)
    return results


__all__ = ["scrape_entity_generic"]
