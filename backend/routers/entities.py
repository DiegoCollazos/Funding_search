"""Endpoints para administrar el banco de entidades financiadoras."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..scraping.adapters.registry import ADAPTER_CHOICES
from ..scraping.runner import run_scrape_for_entity
from ..slugify import slugify as _slugify

router = APIRouter(prefix="/api/entities", tags=["entities"])


def _unique_slug(db: Session, base_slug: str, exclude_id: int | None = None) -> str:
    slug = base_slug
    counter = 2
    while True:
        query = db.query(models.Entity).filter(models.Entity.slug == slug)
        if exclude_id is not None:
            query = query.filter(models.Entity.id != exclude_id)
        if not query.first():
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def _to_out(entity: models.Entity) -> schemas.EntityOut:
    data = schemas.EntityOut.model_validate(entity)
    data.calls_count = len(entity.calls)
    return data


@router.get("", response_model=list[schemas.EntityOut])
def list_entities(scope: str | None = None, active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(models.Entity)
    if scope and scope != "Todas":
        query = query.filter(models.Entity.scope == scope)
    if active_only:
        query = query.filter(models.Entity.active.is_(True))
    entities = query.order_by(models.Entity.scope, models.Entity.name).all()
    return [_to_out(e) for e in entities]


@router.get("/adapters")
def list_adapters():
    return {"adapters": ADAPTER_CHOICES}


@router.post("", response_model=schemas.EntityOut, status_code=201)
def create_entity(payload: schemas.EntityCreate, db: Session = Depends(get_db)):
    slug = _unique_slug(db, _slugify(payload.name))
    entity = models.Entity(
        name=payload.name,
        slug=slug,
        url=payload.url,
        scope=payload.scope,
        country=payload.country,
        entity_type=payload.entity_type,
        adapter=payload.adapter,
        scraper_config=json.dumps(payload.scraper_config or {}),
        schedule_frequency=payload.schedule_frequency,
        active=payload.active,
        last_status="pendiente",
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return _to_out(entity)


@router.get("/{entity_id}", response_model=schemas.EntityOut)
def get_entity(entity_id: int, db: Session = Depends(get_db)):
    entity = db.get(models.Entity, entity_id)
    if not entity:
        raise HTTPException(404, "Entidad no encontrada")
    return _to_out(entity)


@router.put("/{entity_id}", response_model=schemas.EntityOut)
def update_entity(entity_id: int, payload: schemas.EntityUpdate, db: Session = Depends(get_db)):
    entity = db.get(models.Entity, entity_id)
    if not entity:
        raise HTTPException(404, "Entidad no encontrada")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != entity.name:
        entity.name = data["name"]
        entity.slug = _unique_slug(db, _slugify(data["name"]), exclude_id=entity.id)
    if "scraper_config" in data:
        entity.scraper_config = json.dumps(data.pop("scraper_config") or {})
    for field in ("url", "scope", "country", "entity_type", "adapter", "schedule_frequency", "active"):
        if field in data:
            setattr(entity, field, data[field])
    db.commit()
    db.refresh(entity)
    return _to_out(entity)


@router.delete("/{entity_id}", status_code=204)
def delete_entity(entity_id: int, db: Session = Depends(get_db)):
    entity = db.get(models.Entity, entity_id)
    if not entity:
        raise HTTPException(404, "Entidad no encontrada")
    db.delete(entity)
    db.commit()
    return None


@router.post("/{entity_id}/scrape", response_model=schemas.ScrapeLogOut)
def scrape_entity_now(entity_id: int, db: Session = Depends(get_db)):
    entity = db.get(models.Entity, entity_id)
    if not entity:
        raise HTTPException(404, "Entidad no encontrada")
    log = run_scrape_for_entity(db, entity)
    return log


@router.get("/{entity_id}/logs", response_model=list[schemas.ScrapeLogOut])
def entity_logs(entity_id: int, db: Session = Depends(get_db)):
    entity = db.get(models.Entity, entity_id)
    if not entity:
        raise HTTPException(404, "Entidad no encontrada")
    logs = (
        db.query(models.ScrapeLog)
        .filter(models.ScrapeLog.entity_id == entity_id)
        .order_by(models.ScrapeLog.started_at.desc())
        .limit(20)
        .all()
    )
    return logs


__all__ = ["router"]
