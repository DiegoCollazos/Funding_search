"""Registro de adaptadores de scraping disponibles por entidad.

Cada adaptador es una función ``fn(entity) -> list[dict]`` que devuelve una
lista de convocatorias "crudas" con, al menos, las claves ``title`` y
``link``. El motor genérico (``generic_scraper.scrape_entity_generic``) es el
adaptador por defecto y sirve para la gran mayoría de entidades que se
agreguen sólo con una URL; los adaptadores nombrados existen únicamente para
las fuentes donde vale la pena una integración más precisa (ver comentarios
en cada módulo).
"""

from __future__ import annotations

from typing import Callable

from ..generic_scraper import scrape_entity_generic
from .eu import scrape_eu
from .minciencias import scrape_minciencias

_ADAPTERS: dict[str, Callable] = {
    "generic": scrape_entity_generic,
    "eu": lambda entity: scrape_eu(entity),
    "minciencias": scrape_minciencias,
}

ADAPTER_CHOICES = list(_ADAPTERS.keys())


def get_adapter(name: str) -> Callable:
    return _ADAPTERS.get(name, scrape_entity_generic)


__all__ = ["get_adapter", "ADAPTER_CHOICES"]
