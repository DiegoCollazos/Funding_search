"""Heurísticas de extracción de información estructurada a partir de texto libre.

Estas funciones son deliberadamente basadas en reglas (regex + listas de
palabras clave) en lugar de depender de un servicio de IA externo, para que
el sistema funcione sin credenciales ni conexión a APIs de terceros. Están
pensadas para complementarse, no reemplazar, la revisión humana: cuando la
heurística no tiene evidencia suficiente devuelve un estado explícito de
"Por verificar" en vez de arriesgar un dato incorrecto.
"""

from __future__ import annotations

import datetime as dt
import re

_MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
_MONTHS_EN = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

_DATE_FORMATS = [
    "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y", "%B %d, %Y", "%b %d, %Y",
    "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y",
]

_DEADLINE_LABELS = [
    r"fecha de cierre", r"fecha l[ií]mite", r"cierre de (?:la )?convocatoria",
    r"plazo de postulaci[oó]n", r"deadline", r"closing date", r"submission deadline",
]

_AMOUNT_LABELS = [
    r"monto (?:a financiar|total|m[aá]ximo|disponible)?",
    r"presupuesto (?:total|disponible|estimado)?",
    r"valor de la convocatoria", r"budget", r"funding available", r"grant amount",
    r"total funding", r"financiaci[oó]n disponible",
]

_CURRENCY_TOKENS = r"(USD|US\$|EUR|€|\$|COP|GBP|£)"
_MULTIPLIER_WORDS = {
    "millones": 1_000_000, "millón": 1_000_000, "million": 1_000_000,
    "mil": 1_000, "thousand": 1_000, "billones": 1_000_000_000, "billion": 1_000_000_000,
}


def parse_date_generic(date_str: str) -> dt.date | None:
    """Intenta interpretar una fecha en varios formatos comunes (ES/EN)."""
    if not date_str:
        return None
    ds = date_str.strip().strip(".").replace(",", "")
    ds = re.sub(r"\s+", " ", ds)
    # Formatos estándar
    for fmt in _DATE_FORMATS:
        try:
            return dt.datetime.strptime(ds, fmt).date()
        except ValueError:
            continue
    # "25 de septiembre de 2025" / "jueves 25 septiembre 2025 07:00 pm"
    match = re.search(r"(\d{1,2})\s*(?:de\s*)?([A-Za-zÁÉÍÓÚñÑ]+)\s*(?:de\s*)?(\d{4})", ds, re.IGNORECASE)
    if match:
        day, month_name, year = match.groups()
        month = _MONTHS_ES.get(month_name.lower()) or _MONTHS_EN.get(month_name.lower())
        if month:
            try:
                return dt.date(int(year), month, int(day))
            except ValueError:
                return None
    # "September 17, 2025" ya cubierto arriba; intento inverso "2025/09/17"
    match2 = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", ds)
    if match2:
        year, month, day = match2.groups()
        try:
            return dt.date(int(year), int(month), int(day))
        except ValueError:
            return None
    return None


def extract_deadline(text: str) -> str:
    """Busca en el texto una etiqueta de fecha de cierre y devuelve el fragmento con la fecha."""
    if not text:
        return ""
    for label in _DEADLINE_LABELS:
        pattern = rf"{label}\s*[:\-]?\s*([0-9A-Za-zÁÉÍÓÚñÑ,/ ]{{6,40}})"
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip(" .:-")
            if parse_date_generic(candidate) or re.search(r"\d{4}", candidate):
                return candidate
    # Fallback: primera fecha reconocible en el texto
    m2 = re.search(r"\d{1,2}\s*(?:de\s*)?[A-Za-zÁÉÍÓÚñÑ]+\s*(?:de\s*)?\d{4}", text)
    if m2:
        return m2.group(0)
    m3 = re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", text)
    if m3:
        return m3.group(0)
    return ""


def extract_amount(text: str) -> tuple[str, float | None, str]:
    """Devuelve (texto_original, valor_numerico, moneda) del monto de financiación detectado."""
    if not text:
        return "", None, ""
    trailing = r"\s?(?:USD|EUR|COP|GBP)?"
    filler = r"(?:hasta|up to|de)?\s*"
    for label in _AMOUNT_LABELS:
        pattern = (
            rf"{label}\s*[:\-]?\s*{filler}"
            rf"({_CURRENCY_TOKENS}?\s?[\d.,]+\s?(?:millones|mill[oó]n|million|mil|thousand)?{trailing})"
        )
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            snippet = m.group(1).strip()
            value, currency = _parse_amount_value(snippet, text[max(0, m.start() - 20):m.start()])
            return snippet, value, currency
    # Fallback: cualquier símbolo de moneda seguido de dígitos en el texto
    m2 = re.search(
        rf"{_CURRENCY_TOKENS}\s?[\d.,]+\s?(?:millones|mill[oó]n|million|mil|thousand)?{trailing}",
        text, re.IGNORECASE,
    )
    if m2:
        snippet = m2.group(0).strip()
        value, currency = _parse_amount_value(snippet, "")
        return snippet, value, currency
    return "", None, ""


def _parse_amount_value(snippet: str, context_before: str) -> tuple[float | None, str]:
    explicit_code = re.search(r"\b(USD|EUR|COP|GBP)\b", snippet, re.IGNORECASE)
    if explicit_code:
        currency = explicit_code.group(1).upper()
    else:
        symbol_match = re.search(r"(US\$|€|\$|£)", snippet)
        symbol = symbol_match.group(0) if symbol_match else ""
        currency = {"US$": "USD", "$": "USD", "€": "EUR", "£": "GBP"}.get(symbol, "")
        if not currency and "cop" in context_before.lower():
            currency = "COP"
    number_match = re.search(r"[\d][\d.,]*", snippet)
    if not number_match:
        return None, currency
    raw_number = number_match.group(0)
    # Normaliza separador de miles/decimales: si hay ambos , y . se asume el último como decimal.
    if "," in raw_number and "." in raw_number:
        if raw_number.rfind(",") > raw_number.rfind("."):
            raw_number = raw_number.replace(".", "").replace(",", ".")
        else:
            raw_number = raw_number.replace(",", "")
    elif "," in raw_number:
        # Asumimos coma como separador de miles (común en formatos EN) salvo que tenga 2 decimales
        parts = raw_number.split(",")
        if len(parts[-1]) == 2:
            raw_number = raw_number.replace(",", ".")
        else:
            raw_number = raw_number.replace(",", "")
    elif "." in raw_number:
        parts = raw_number.split(".")
        # Varios puntos (p.ej. "500.000.000") o un único punto seguido de un
        # grupo de 3 dígitos (p.ej. "500.000") son separadores de miles en
        # formato latino/europeo, no un punto decimal.
        if len(parts) > 2 or len(parts[-1]) == 3:
            raw_number = raw_number.replace(".", "")
    try:
        value = float(raw_number)
    except ValueError:
        return None, currency
    multiplier = 1
    lower_snippet = snippet.lower()
    for word, factor in _MULTIPLIER_WORDS.items():
        if word in lower_snippet:
            multiplier = factor
            break
    return value * multiplier, currency


_OBJECTIVE_LABELS = [
    r"objetivo(?:s)? (?:general(?:es)?|espec[ií]fico[s]?|de la convocatoria)?",
    r"prop[oó]sito", r"finalidad",
    r"objective[s]?", r"aim[s]?", r"purpose", r"scope of the call",
]


def extract_objective(description: str, title: str = "") -> str:
    """Extrae el párrafo de 'objetivo' si está etiquetado; si no, usa las primeras oraciones."""
    if not description:
        return title
    for label in _OBJECTIVE_LABELS:
        pattern = rf"{label}\s*[:\-]?\s*(.{{20,600}}?)(?:\n\n|\.\s*\n|$)"
        m = re.search(pattern, description, re.IGNORECASE | re.DOTALL)
        if m:
            snippet = re.sub(r"\s+", " ", m.group(1)).strip()
            if snippet:
                return snippet[:600]
    sentences = re.split(r"(?<=[.!?])\s+", description.strip())
    return " ".join(sentences[:3])[:600] if sentences else description[:600]


# --------------------------------------------------------------------------
# Viabilidad de participación de una universidad pública
# --------------------------------------------------------------------------

_UNIV_POSITIVE = [
    "universidades públicas", "universidad pública", "instituciones de educación superior",
    "ies públicas", "entidades públicas", "instituciones públicas",
    "organismos públicos de investigación", "personas jurídicas de derecho público",
    "cualquier persona jurídica", "entidades sin ánimo de lucro", "entidades territoriales",
    "public universities", "state universities", "higher education institutions",
    "public research organisations", "public research organizations", "any legal entity",
    "research organisations", "universities and research centres", "academic institutions",
    "government agencies", "public sector entities", "public bodies",
]
_UNIV_PARTNER_ONLY = [
    "en alianza", "como aliado", "como socio", "en consorcio", "as a partner",
    "consortium", "in partnership with", "en cooperación con universidades",
    "joint proposals", "propuestas conjuntas",
]
_UNIV_NEGATIVE = [
    "solo empresas privadas", "únicamente sector privado", "exclusivamente privado",
    "excluye entidades estatales", "excluye entidades públicas", "private sector only",
    "for-profit organisations only", "for-profit organizations only", "solo pymes privadas",
    "microempresas y pequeñas empresas privadas",
]


def assess_university_eligibility(text: str) -> tuple[str, str]:
    """Heurística de viabilidad para que una universidad pública se presente como ejecutora o aliada.

    Devuelve (clasificación, nota). La clasificación es una de:
    'Sí (ejecutora)', 'Sí (aliada)', 'Sí (ejecutora o aliada)', 'No', 'Por verificar'.
    Esta es una señal orientativa basada en palabras clave del texto público de la
    convocatoria; siempre se recomienda confirmar en las bases oficiales.
    """
    if not text:
        return "Por verificar", "No hay suficiente texto público para evaluar los requisitos de elegibilidad."
    lower = text.lower()

    matched_negative = [kw for kw in _UNIV_NEGATIVE if kw in lower]
    if matched_negative:
        return (
            "No",
            f"El texto sugiere restricciones que excluirían a una universidad pública "
            f"(coincide con: \"{matched_negative[0]}\"). Verificar bases completas.",
        )

    matched_positive = [kw for kw in _UNIV_POSITIVE if kw in lower]
    matched_partner = [kw for kw in _UNIV_PARTNER_ONLY if kw in lower]

    if matched_positive and matched_partner:
        return (
            "Sí (ejecutora o aliada)",
            f"Se mencionan universidades/entidades públicas como elegibles "
            f"(\"{matched_positive[0]}\") y también esquemas de alianza/consorcio "
            f"(\"{matched_partner[0]}\").",
        )
    if matched_positive:
        return (
            "Sí (ejecutora)",
            f"El texto menciona explícitamente a universidades o entidades públicas "
            f"como elegibles (\"{matched_positive[0]}\").",
        )
    if matched_partner:
        return (
            "Sí (aliada)",
            f"El texto menciona esquemas de consorcio/alianza (\"{matched_partner[0]}\"); "
            f"una universidad pública podría participar como socio, no necesariamente como ejecutora principal.",
        )
    return (
        "Por verificar",
        "No se encontraron términos claros de elegibilidad en el texto disponible; "
        "revisar los términos de referencia o bases completas de la convocatoria.",
    )


__all__ = [
    "parse_date_generic",
    "extract_deadline",
    "extract_amount",
    "extract_objective",
    "assess_university_eligibility",
]
