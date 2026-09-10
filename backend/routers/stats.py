"""Endpoint de estadísticas para el panel principal de la herramienta."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=schemas.StatsOut)
def get_stats(db: Session = Depends(get_db)):
    total_entities = db.query(models.Entity).count()
    active_entities = db.query(models.Entity).filter(models.Entity.active.is_(True)).count()
    total_calls = db.query(models.Call).count()
    open_calls = db.query(models.Call).filter(models.Call.status != "Cerrada").count()
    national_calls = db.query(models.Call).filter(
        models.Call.scope == "Nacional", models.Call.status != "Cerrada"
    ).count()
    international_calls = db.query(models.Call).filter(
        models.Call.scope == "Internacional", models.Call.status != "Cerrada"
    ).count()
    return schemas.StatsOut(
        total_entities=total_entities,
        active_entities=active_entities,
        total_calls=total_calls,
        open_calls=open_calls,
        national_calls=national_calls,
        international_calls=international_calls,
    )


__all__ = ["router"]
