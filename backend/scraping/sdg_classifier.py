"""Clasificación temática y por Objetivos de Desarrollo Sostenible (ODS).

Extiende el enfoque original del proyecto (mapeo de palabras clave) con
términos en español e inglés para cubrir tanto fuentes nacionales como
internacionales.
"""

from __future__ import annotations

SDG_NAMES = {
    "1": "Fin de la pobreza",
    "2": "Hambre cero",
    "3": "Salud y bienestar",
    "4": "Educación de calidad",
    "5": "Igualdad de género",
    "6": "Agua limpia y saneamiento",
    "7": "Energía asequible y no contaminante",
    "8": "Trabajo decente y crecimiento económico",
    "9": "Industria, innovación e infraestructura",
    "10": "Reducción de las desigualdades",
    "11": "Ciudades y comunidades sostenibles",
    "12": "Producción y consumo responsables",
    "13": "Acción por el clima",
    "14": "Vida submarina",
    "15": "Vida de ecosistemas terrestres",
    "16": "Paz, justicia e instituciones sólidas",
    "17": "Alianzas para lograr los objetivos",
}

_SDG_KEYWORDS: dict[str, list[str]] = {
    "1": ["pobreza", "poverty", "ingresos mínimos", "vulnerabilidad económica"],
    "2": ["hambre", "hunger", "seguridad alimentaria", "food security", "agricultura", "agriculture", "nutrición"],
    "3": ["salud", "health", "bienestar", "well-being", "enfermedad", "disease", "medicina", "clinical", "vacun"],
    "4": ["educación", "education", "escuela", "school", "universidad", "university", "formación", "skills"],
    "5": ["igualdad de género", "gender equality", "mujer", "women", "género", "gender"],
    "6": ["agua", "water", "saneamiento", "sanitation", "hídrico", "hidráulica"],
    "7": ["energía", "energy", "renovable", "renewable", "electrificación", "hidrógeno", "hydrogen", "solar", "eólica"],
    "8": ["empleo", "employment", "trabajo decente", "decent work", "economía", "economic growth", "emprendimiento", "entrepreneurship"],
    "9": ["industria", "industry", "innovación", "innovation", "infraestructura", "infrastructure", "tecnología", "technology", "manufactura"],
    "10": ["desigualdad", "inequality", "inclusión", "inclusion", "migración", "migration"],
    "11": ["ciudades", "cities", "comunidades sostenibles", "urbanismo", "urban", "movilidad", "mobility", "vivienda", "housing"],
    "12": ["consumo responsable", "consumption", "producción sostenible", "production", "residuos", "waste", "economía circular", "circular economy"],
    "13": ["cambio climático", "climate change", "carbono", "carbon", "clima", "climate action", "adaptación climática"],
    "14": ["océano", "ocean", "mar", "marine", "pesca", "fisheries", "vida marina"],
    "15": ["ecosistema", "ecosystem", "bosque", "forest", "biodiversidad", "biodiversity", "deforestación"],
    "16": ["paz", "peace", "justicia", "justice", "instituciones", "institutions", "gobernanza", "governance", "derechos humanos", "human rights"],
    "17": ["alianzas", "partnerships", "cooperación internacional", "international cooperation", "financiación para el desarrollo", "cooperación sur-sur"],
}


def classify_sdg(text: str) -> list[str]:
    """Devuelve la lista de números ODS cuyas palabras clave aparecen en el texto.

    Si no hay coincidencias devuelve ``["unknown"]``.
    """
    if not text:
        return ["unknown"]
    lower = text.lower()
    matched = [goal for goal, keywords in _SDG_KEYWORDS.items() if any(k in lower for k in keywords)]
    return matched if matched else ["unknown"]


def extract_theme_keywords(text: str, max_keywords: int = 8) -> list[str]:
    """Extrae palabras/frases temáticas relevantes de forma simple (sin NLP pesado).

    Se apoya en la misma lista de palabras clave de ODS más un pequeño conjunto de
    líneas temáticas comunes en convocatorias de I+D+i, y devuelve las que
    aparecen literalmente en el texto (deduplicadas, en orden de aparición).
    """
    if not text:
        return []
    lower = text.lower()
    candidates: list[str] = []
    for keywords in _SDG_KEYWORDS.values():
        candidates.extend(keywords)
    candidates.extend([
        "inteligencia artificial", "artificial intelligence", "biotecnología", "biotechnology",
        "ciberseguridad", "cybersecurity", "cambio climático", "salud pública", "public health",
        "transformación digital", "digital transformation", "economía circular", "energías limpias",
        "ciencia abierta", "open science", "género", "innovación social", "social innovation",
    ])
    found: list[str] = []
    for kw in candidates:
        if kw in lower and kw not in found:
            found.append(kw)
        if len(found) >= max_keywords:
            break
    return found


def summarize_text(text: str, word_limit: int = 120) -> str:
    """Resumen simple por truncado, preservado del proyecto original como fallback."""
    if not text:
        return ""
    words = text.split()
    if len(words) <= word_limit:
        return text.strip()
    return " ".join(words[:word_limit]) + "..."


__all__ = ["classify_sdg", "extract_theme_keywords", "summarize_text", "SDG_NAMES"]
