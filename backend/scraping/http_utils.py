"""Utilidades HTTP compartidas por los adaptadores de scraping."""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
}


def fetch_page(url: str, *, timeout: int = 30, extra_headers: dict | None = None) -> str:
    """Descarga una URL y devuelve el HTML como texto. Lanza en caso de error HTTP."""
    headers = dict(DEFAULT_HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    response = requests.get(url, timeout=timeout, headers=headers)
    response.raise_for_status()
    return response.text


def fetch_json(url: str, *, method: str = "GET", timeout: int = 30, **kwargs):
    headers = dict(DEFAULT_HEADERS)
    headers["Accept"] = "application/json"
    headers.update(kwargs.pop("headers", {}) or {})
    response = requests.request(method, url, timeout=timeout, headers=headers, **kwargs)
    response.raise_for_status()
    return response.json()


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def visible_text(soup: BeautifulSoup, limit: int | None = None) -> str:
    """Extrae texto visible de una página, colapsando espacios repetidos."""
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    joined = "\n".join(lines)
    return joined[:limit] if limit else joined


__all__ = ["fetch_page", "fetch_json", "parse_html", "visible_text", "DEFAULT_HEADERS"]
