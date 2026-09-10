"""Esquemas Pydantic para la API REST."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------
# Entidades
# --------------------------------------------------------------------------

class EntityBase(BaseModel):
    name: str
    url: str
    scope: str = Field(default="Internacional", pattern="^(Nacional|Internacional)$")
    country: str = ""
    entity_type: str = "Otro"
    adapter: str = "generic"
    scraper_config: dict = {}
    schedule_frequency: str = Field(default="semanal", pattern="^(manual|diario|semanal|mensual)$")
    active: bool = True


class EntityCreate(EntityBase):
    pass


class EntityUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    scope: str | None = None
    country: str | None = None
    entity_type: str | None = None
    adapter: str | None = None
    scraper_config: dict | None = None
    schedule_frequency: str | None = None
    active: bool | None = None


class EntityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    url: str
    scope: str
    country: str
    entity_type: str
    adapter: str
    schedule_frequency: str
    active: bool
    last_scraped_at: dt.datetime | None
    last_status: str
    last_message: str
    created_at: dt.datetime
    calls_count: int = 0


# --------------------------------------------------------------------------
# Convocatorias
# --------------------------------------------------------------------------

class CallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_id: int
    entity_name: str = ""
    title: str
    link: str
    objective: str
    description: str
    opening_date_text: str
    deadline_date_text: str
    deadline_date: dt.date | None
    amount_text: str
    amount_value: float | None
    amount_currency: str
    scope: str
    sdg_list: list[str] = []
    theme_keywords: list[str] = []
    university_eligibility: str
    university_eligibility_note: str
    status: str
    last_seen_at: dt.datetime


class CallSearchRequest(BaseModel):
    keyword: str = ""
    theme: str = ""
    sdg: str = ""  # "1".."17" o vacío
    scope: str = "Todas"  # Nacional | Internacional | Todas
    only_open: bool = True
    entity_id: int | None = None
    limit: int = 100


class IdentifyRequest(BaseModel):
    url: str = ""
    text: str = ""


class IdentifyResult(BaseModel):
    scope: str
    scope_confidence: str
    title: str
    objective: str
    deadline_date_text: str
    amount_text: str
    university_eligibility: str
    university_eligibility_note: str
    sdg_list: list[str]
    raw_excerpt: str


class ScrapeLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_id: int
    started_at: dt.datetime
    finished_at: dt.datetime | None
    status: str
    message: str
    calls_found: int
    calls_new: int


class StatsOut(BaseModel):
    total_entities: int
    active_entities: int
    total_calls: int
    open_calls: int
    national_calls: int
    international_calls: int
