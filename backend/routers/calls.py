"""Endpoints de búsqueda y consulta de convocatorias."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/calls", tags=["calls"])


def _to_out(call: models.Call) -> schemas.CallOut:
    return schemas.CallOut(
        id=call.id,
        entity_id=call.entity_id,
        entity_name=call.entity.name if call.entity else "",
        title=call.title,
        link=call.link,
        objective=call.objective,
        description=call.description,
        opening_date_text=call.opening_date_text,
        deadline_date_text=call.deadline_date_text,
        deadline_date=call.deadline_date,
        amount_text=call.amount_text,
        amount_value=call.amount_value,
        amount_currency=call.amount_currency,
        scope=call.scope,
        sdg_list=[s for s in (call.sdg_list or "").split(",") if s],
        theme_keywords=[k for k in (call.theme_keywords or "").split(",") if k],
        university_eligibility=call.university_eligibility,
        university_eligibility_note=call.university_eligibility_note,
        status=call.status,
        last_seen_at=call.last_seen_at,
    )


@router.get("/search", response_model=list[schemas.CallOut])
def search_calls(
    keyword: str = "",
    theme: str = "",
    sdg: str = "",
    scope: str = "Todas",
    only_open: bool = True,
    entity_id: int | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    query = db.query(models.Call).join(models.Entity)

    if scope and scope != "Todas":
        query = query.filter(models.Call.scope == scope)
    if entity_id:
        query = query.filter(models.Call.entity_id == entity_id)
    if only_open:
        query = query.filter(models.Call.status != "Cerrada")
    if sdg:
        query = query.filter(models.Call.sdg_list.like(f"%{sdg}%"))
    if keyword:
        like = f"%{keyword.lower()}%"
        query = query.filter(
            or_(
                models.Call.title.ilike(like),
                models.Call.description.ilike(like),
                models.Call.objective.ilike(like),
            )
        )
    if theme:
        like_theme = f"%{theme.lower()}%"
        query = query.filter(
            or_(
                models.Call.theme_keywords.ilike(like_theme),
                models.Call.description.ilike(like_theme),
                models.Call.title.ilike(like_theme),
            )
        )

    calls = (
        query.order_by(models.Call.deadline_date.is_(None), models.Call.deadline_date.asc())
        .limit(limit)
        .all()
    )
    return [_to_out(c) for c in calls]


@router.get("/{call_id}", response_model=schemas.CallOut)
def get_call(call_id: int, db: Session = Depends(get_db)):
    call = db.get(models.Call, call_id)
    if not call:
        raise HTTPException(404, "Convocatoria no encontrada")
    return _to_out(call)


@router.post("/refresh-status", status_code=200)
def refresh_status(db: Session = Depends(get_db)):
    """Recalcula 'Vigente'/'Cerrada' de todas las convocatorias según la fecha de hoy."""
    today = dt.date.today()
    calls = db.query(models.Call).filter(models.Call.deadline_date.isnot(None)).all()
    updated = 0
    for call in calls:
        new_status = "Vigente" if call.deadline_date >= today else "Cerrada"
        if call.status != new_status:
            call.status = new_status
            updated += 1
    db.commit()
    return {"updated": updated}


__all__ = ["router"]
