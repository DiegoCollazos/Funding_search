"""Utilidad compartida para generar slugs estables (usados como id de entidad)."""

from __future__ import annotations

import re
import unicodedata


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "entidad"


__all__ = ["slugify"]
