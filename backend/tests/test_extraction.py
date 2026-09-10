import datetime as dt

from backend.scraping.extraction import (
    assess_university_eligibility,
    extract_amount,
    extract_deadline,
    extract_objective,
    parse_date_generic,
)
from backend.scraping.sdg_classifier import classify_sdg
from backend.scraping.scope_classifier import classify_scope


def test_parse_date_generic_formats():
    assert parse_date_generic("25 de septiembre de 2025") == dt.date(2025, 9, 25)
    assert parse_date_generic("September 17, 2025") == dt.date(2025, 9, 17)
    assert parse_date_generic("17/09/2025") == dt.date(2025, 9, 17)
    assert parse_date_generic("2025-09-17") == dt.date(2025, 9, 17)
    assert parse_date_generic("") is None
    assert parse_date_generic("no es una fecha") is None


def test_extract_deadline_finds_labelled_date():
    text = "Requisitos: ... Fecha de cierre: 15 de diciembre de 2026. Otros detalles."
    assert "15 de diciembre de 2026" in extract_deadline(text)


def test_extract_amount_detects_currency_code_after_symbol():
    text = "Monto a financiar: hasta $500.000.000 COP por proyecto."
    snippet, value, currency = extract_amount(text)
    assert currency == "COP"
    assert value == 500_000_000


def test_extract_amount_detects_million_multiplier():
    text = "Budget: EUR 3 millones available for this call."
    snippet, value, currency = extract_amount(text)
    assert currency == "EUR"
    assert value == 3_000_000


def test_extract_objective_prefers_labelled_section():
    text = "Introducción larga. Objetivo: fortalecer capacidades científicas del país. Fin."
    objective = extract_objective(text)
    assert "fortalecer capacidades" in objective


def test_university_eligibility_positive():
    text = "Podrán participar universidades públicas y privadas como ejecutoras del proyecto."
    result, note = assess_university_eligibility(text)
    assert result == "Sí (ejecutora)"
    assert "universidades públicas" in note


def test_university_eligibility_negative():
    text = "Esta convocatoria excluye entidades públicas; solo empresas privadas pueden postular."
    result, _note = assess_university_eligibility(text)
    assert result == "No"


def test_university_eligibility_unknown_without_signal():
    result, _note = assess_university_eligibility("Texto genérico sin información de elegibilidad.")
    assert result == "Por verificar"


def test_classify_sdg_health_keywords():
    assert "3" in classify_sdg("Convocatoria de investigación en salud pública y bienestar.")


def test_classify_sdg_unknown_when_no_match():
    assert classify_sdg("xyz") == ["unknown"]


def test_classify_scope_national_by_domain():
    scope, _ = classify_scope(url="https://minciencias.gov.co/convocatorias/todas")
    assert scope == "Nacional"


def test_classify_scope_international_default():
    scope, _ = classify_scope(url="https://wellcome.org/grant-funding/schemes")
    assert scope == "Internacional"
