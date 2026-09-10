"""Endpoint de identificación rápida de una convocatoria puntual (URL o texto)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import schemas
from ..scraping.identify import identify_call

router = APIRouter(prefix="/api/identify", tags=["identify"])


@router.post("", response_model=schemas.IdentifyResult)
def identify(payload: schemas.IdentifyRequest):
    if not payload.url and not payload.text:
        raise HTTPException(400, "Debe indicar una URL o pegar el texto de la convocatoria.")
    try:
        result = identify_call(url=payload.url.strip(), text=payload.text.strip())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"No se pudo obtener/analizar la página: {exc}") from exc
    return result


__all__ = ["router"]
