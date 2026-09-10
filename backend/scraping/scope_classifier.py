"""Clasificación heurística de una convocatoria como Nacional o Internacional.

Para entidades registradas en el banco de entidades el alcance ya se define
explícitamente al darlas de alta (ver ``models.Entity.scope``). Este módulo
se usa sobre todo en la herramienta de "Identificación rápida", donde el
usuario pega la URL de una convocatoria puntual que no necesariamente
pertenece a una entidad ya registrada.
"""

from __future__ import annotations

from urllib.parse import urlparse

# Dominios de nivel superior / fragmentos asociados a Colombia (mercado nacional
# de referencia del proyecto). Se puede ampliar a otros países si se requiere.
_NATIONAL_TLD_HINTS = [".gov.co", ".edu.co", ".mil.co", ".org.co", ".com.co"]
_NATIONAL_KEYWORDS = [
    "minciencias", "mincultura", "mintic", "minambiente", "minenergia", "minenergía",
    "mineducacion", "mineducación", "colombia", "colombiano", "colombiana",
    "departamento administrativo", "alcaldía", "gobernación", "regalías", "regalias",
    "función pública", "dnp.gov.co",
]
_INTERNATIONAL_KEYWORDS = [
    "european commission", "horizon europe", "wellcome trust", "world bank",
    "usaid", "unesco", "undp", "unicef", "idrc", "ibro", "erasmus", "daad",
    "fontagro", "iadb", "bid.org", "grants.gov", "nih.gov", "cordis.europa.eu",
]


def classify_scope(url: str = "", text: str = "") -> tuple[str, str]:
    """Devuelve (alcance, confianza_explicada).

    alcance: "Nacional" o "Internacional".
    """
    url_l = (url or "").lower()
    text_l = (text or "").lower()
    host = urlparse(url_l).netloc if url_l else ""

    for hint in _NATIONAL_TLD_HINTS:
        if hint in host:
            return "Nacional", f"El dominio de la URL contiene '{hint}', asociado a Colombia."

    for kw in _NATIONAL_KEYWORDS:
        if kw in url_l or kw in text_l:
            return "Nacional", f"Se encontró el término '{kw}', asociado a entidades colombianas."

    for kw in _INTERNATIONAL_KEYWORDS:
        if kw in url_l or kw in text_l:
            return "Internacional", f"Se encontró el término '{kw}', asociado a organismos internacionales."

    if host.endswith(".co"):
        return "Nacional", "El dominio termina en '.co'."

    return "Internacional", "No se hallaron señales explícitas de Colombia; se asume alcance internacional por defecto."


__all__ = ["classify_scope"]
