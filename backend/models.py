"""Modelos SQLAlchemy: entidades financiadoras, convocatorias y bitácora de scraping."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Entity(Base):
    """Una entidad financiadora (ministerio, agencia, fundación, cooperación...)."""

    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), default="Internacional")  # Nacional | Internacional
    country: Mapped[str] = mapped_column(String(100), default="")
    entity_type: Mapped[str] = mapped_column(String(50), default="Otro")

    # Nombre del adaptador de scraping a usar ("generic" o uno registrado, p.ej. "eu", "minciencias")
    adapter: Mapped[str] = mapped_column(String(50), default="generic")
    # Configuración de selectores CSS para el motor genérico, serializada como JSON.
    scraper_config: Mapped[str] = mapped_column(Text, default="{}")

    # Frecuencia de scraping programado: manual | diario | semanal | mensual
    schedule_frequency: Mapped[str] = mapped_column(String(20), default="semanal")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    last_scraped_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[str] = mapped_column(String(20), default="pendiente")  # pendiente|ok|error
    last_message: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    calls: Mapped[list["Call"]] = relationship(back_populates="entity", cascade="all, delete-orphan")
    logs: Mapped[list["ScrapeLog"]] = relationship(back_populates="entity", cascade="all, delete-orphan")


class Call(Base):
    """Una convocatoria de financiación detectada para una entidad."""

    __tablename__ = "calls"
    __table_args__ = (UniqueConstraint("entity_id", "link", name="uq_call_entity_link"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    link: Mapped[str] = mapped_column(String(1500), nullable=False)

    objective: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")

    opening_date_text: Mapped[str] = mapped_column(String(100), default="")
    deadline_date_text: Mapped[str] = mapped_column(String(100), default="")
    deadline_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    amount_text: Mapped[str] = mapped_column(String(300), default="")
    amount_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount_currency: Mapped[str] = mapped_column(String(10), default="")

    scope: Mapped[str] = mapped_column(String(20), default="Internacional")  # Nacional | Internacional
    sdg_list: Mapped[str] = mapped_column(String(200), default="")  # csv de números ODS
    theme_keywords: Mapped[str] = mapped_column(String(500), default="")

    university_eligibility: Mapped[str] = mapped_column(String(30), default="Por verificar")
    university_eligibility_note: Mapped[str] = mapped_column(Text, default="")

    status: Mapped[str] = mapped_column(String(20), default="Vigente")  # Vigente | Cerrada | Por confirmar

    first_seen_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    last_seen_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    entity: Mapped["Entity"] = relationship(back_populates="calls")


class ScrapeLog(Base):
    """Registro de cada corrida de scraping (manual o programada) por entidad."""

    __tablename__ = "scrape_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), nullable=False)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ok")  # ok | error
    message: Mapped[str] = mapped_column(Text, default="")
    calls_found: Mapped[int] = mapped_column(Integer, default=0)
    calls_new: Mapped[int] = mapped_column(Integer, default=0)

    entity: Mapped["Entity"] = relationship(back_populates="logs")
