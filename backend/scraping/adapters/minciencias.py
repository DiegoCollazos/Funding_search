"""Adaptador específico para MinCiencias (Colombia).

Se conserva como adaptador "a medida" (en vez de dejarlo en modo genérico)
porque la fecha de cierre real sólo aparece en la página de detalle, dentro
de una fila de tabla identificable por una clase CSS particular. Este
patrón —adaptador especializado sólo donde aporta valor, motor genérico para
todo lo demás— es el enfoque híbrido recomendado para este proyecto: no hay
que escribir un script por cada una de las decenas de entidades posibles,
pero se puede afinar el scraping de las fuentes más importantes o más
difíciles.

Basado en la lógica del ``minciencias_scraper.py`` del proyecto original.
"""

from __future__ import annotations

from ..http_utils import fetch_page, parse_html

LISTING_URL = "https://minciencias.gov.co/convocatorias/todas"
BASE_URL = "https://minciencias.gov.co"


def scrape_minciencias(entity) -> list[dict]:
    url = entity.url or LISTING_URL
    html = fetch_page(url)
    soup = parse_html(html)
    tbody = soup.find("tbody")
    if not tbody:
        return []
    rows = tbody.find_all("tr")
    results: list[dict] = []
    for row in rows[:15]:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        title_cell = cells[1] if len(cells) > 1 else cells[0]
        link_tag = title_cell.find("a", href=True)
        if not link_tag:
            continue
        title = link_tag.get_text(strip=True)
        href = link_tag["href"]
        link = href if href.startswith("http") else BASE_URL + href
        description = cells[2].get_text(" ", strip=True) if len(cells) > 2 else ""
        opening_date_text = cells[4].get_text(" ", strip=True) if len(cells) > 4 else ""

        deadline_date_text = ""
        try:
            detail_html = fetch_page(link)
            detail_soup = parse_html(detail_html)
            for drow in detail_soup.find_all("tr"):
                header_cell = drow.find("td", class_="views-field-field-numero")
                if header_cell and "Cierre" in header_cell.get_text(strip=True):
                    value_cell = drow.find("td", class_="views-field-body")
                    if value_cell:
                        deadline_date_text = value_cell.get_text(strip=True)
                    break
            raw_text = description + "\n" + detail_soup.get_text("\n", strip=True)[:8000]
        except Exception:
            raw_text = description

        results.append({
            "title": title,
            "link": link,
            "description": description,
            "opening_date_text": opening_date_text,
            "deadline_date_text": deadline_date_text,
            "raw_text": raw_text,
        })
    return results


__all__ = ["scrape_minciencias"]
