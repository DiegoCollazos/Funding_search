"""Carga inicial del banco de entidades (y datos de ejemplo) en una base nueva.

Las entidades listadas aquí son las mismas fuentes que ya cubría el proyecto
original (ver ``PAGINAS.txt`` y ``Ministerios.txt`` del repositorio previo),
migradas del modelo de "un script por sitio" a filas configurables del banco
de entidades. El usuario puede editarlas, desactivarlas o agregar nuevas
desde la pestaña "Administrar entidades" sin tocar código.
"""

from __future__ import annotations

import datetime as dt
import re

from sqlalchemy.orm import Session

from . import models

_SEED_ENTITIES = [
    # -- Internacionales --------------------------------------------------
    dict(
        name="European Commission – Funding & Tenders Portal",
        url="https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/calls-for-proposals",
        scope="Internacional", country="Unión Europea", entity_type="Programa marco",
        adapter="eu",
    ),
    dict(
        name="Wellcome Trust", url="https://wellcome.org/grant-funding/schemes",
        scope="Internacional", country="Reino Unido", entity_type="Fundación", adapter="generic",
    ),
    dict(
        name="Research Council of Finland (Academy of Finland)",
        url="https://www.aka.fi/en/research-funding/apply-for-funding/calls-for-applications/",
        scope="Internacional", country="Finlandia", entity_type="Agencia pública", adapter="generic",
    ),
    dict(
        name="ANR – Agence Nationale de la Recherche",
        url="https://anr.fr/en/call-for-proposals-details/", scope="Internacional",
        country="Francia", entity_type="Agencia pública", adapter="generic",
    ),
    dict(
        name="IBRO – International Brain Research Organization",
        url="https://ibro.org/grants-prizes/", scope="Internacional",
        country="Internacional", entity_type="Organización científica", adapter="generic",
    ),
    dict(
        name="IDRC – International Development Research Centre",
        url="https://idrc-crdi.ca/en/funding", scope="Internacional",
        country="Canadá", entity_type="Agencia de cooperación", adapter="generic",
    ),
    dict(
        name="FONTAGRO", url="https://www.fontagro.org/new/convocatorias/",
        scope="Internacional", country="Internacional (América Latina)",
        entity_type="Fondo multilateral", adapter="generic",
    ),
    # -- Nacionales (Colombia) ---------------------------------------------
    dict(
        name="MinCiencias – Convocatorias", url="https://minciencias.gov.co/convocatorias/todas",
        scope="Nacional", country="Colombia", entity_type="Ministerio", adapter="minciencias",
    ),
    dict(
        name="MinAmbiente – Convocatorias", url="https://www.minambiente.gov.co/convocatorias/",
        scope="Nacional", country="Colombia", entity_type="Ministerio", adapter="generic",
    ),
    dict(
        name="MinCultura – Convocatorias",
        url="https://www.mincultura.gov.co/convocatorias/Paginas/default.aspx",
        scope="Nacional", country="Colombia", entity_type="Ministerio", adapter="generic",
    ),
    dict(
        name="MinTIC – Convocatorias", url="https://www.mintic.gov.co/portal/inicio/Convocatorias/",
        scope="Nacional", country="Colombia", entity_type="Ministerio", adapter="generic",
    ),
    dict(
        name="MinEducación – Convocatorias",
        url="https://www.mineducacion.gov.co/portal/convocatorias/",
        scope="Nacional", country="Colombia", entity_type="Ministerio", adapter="generic",
    ),
    dict(
        name="MinEnergía – Convocatorias", url="https://www.minenergia.gov.co/es/convocatorias/",
        scope="Nacional", country="Colombia", entity_type="Ministerio", adapter="generic",
    ),
]


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def seed_entities_if_empty(db: Session) -> int:
    if db.query(models.Entity).count() > 0:
        return 0
    created = 0
    for spec in _SEED_ENTITIES:
        slug = _slugify(spec["name"])
        entity = models.Entity(
            name=spec["name"],
            slug=slug,
            url=spec["url"],
            scope=spec["scope"],
            country=spec["country"],
            entity_type=spec["entity_type"],
            adapter=spec["adapter"],
            scraper_config="{}",
            schedule_frequency="semanal",
            active=True,
            last_status="pendiente",
        )
        db.add(entity)
        created += 1
    db.commit()
    return created


_DEMO_CALLS = [
    dict(
        entity_slug="minciencias-convocatorias",
        title="Convocatoria para el fortalecimiento de grupos de investigación (ejemplo)",
        objective=(
            "Financiar proyectos de investigación, desarrollo tecnológico e innovación "
            "ejecutados por grupos reconocidos, con participación de instituciones de educación superior."
        ),
        deadline_days=45,
        amount_text="Hasta $800.000.000 COP por proyecto",
        amount_value=800_000_000, amount_currency="COP",
        eligibility="Sí (ejecutora)",
        eligibility_note="Convocatoria abierta a universidades públicas y privadas reconocidas por el Ministerio de Educación.",
        sdg="4,9",
    ),
    dict(
        entity_slug="european-commission-funding-tenders-portal",
        title="Horizon Europe – Cluster Health call (ejemplo)",
        objective=(
            "Support research consortia addressing public health challenges, including "
            "participation of public research organisations and universities as beneficiaries."
        ),
        deadline_days=90,
        amount_text="EUR 3,000,000 total budget per project",
        amount_value=3_000_000, amount_currency="EUR",
        eligibility="Sí (ejecutora o aliada)",
        eligibility_note="La convocatoria permite participar como beneficiario principal o como socio en consorcio; incluye universidades públicas.",
        sdg="3",
    ),
    dict(
        entity_slug="fontagro",
        title="Convocatoria de innovación agroalimentaria (ejemplo)",
        objective="Cofinanciar proyectos de innovación tecnológica para la agricultura familiar y sostenible en América Latina y el Caribe.",
        deadline_days=60,
        amount_text="USD 200,000 por proyecto",
        amount_value=200_000, amount_currency="USD",
        eligibility="Sí (aliada)",
        eligibility_note="Se requiere consorcio con al menos dos países; universidades públicas pueden participar como aliadas del proponente.",
        sdg="2",
    ),
]


def seed_demo_calls_if_empty(db: Session) -> int:
    """Inserta un puñado de convocatorias de ejemplo para que la herramienta no
    se vea vacía en un primer uso sin conexión. Quedan claramente marcadas como
    ejemplo en su descripción y desaparecen solas de los resultados "vigentes"
    una vez expira su fecha de cierre simulada; se reemplazan por datos reales
    en cuanto se ejecuta un scraping real sobre la misma entidad."""
    if db.query(models.Call).count() > 0:
        return 0
    created = 0
    today = dt.date.today()
    for spec in _DEMO_CALLS:
        entity = db.query(models.Entity).filter(models.Entity.slug == spec["entity_slug"]).first()
        if not entity:
            continue
        deadline = today + dt.timedelta(days=spec["deadline_days"])
        call = models.Call(
            entity_id=entity.id,
            title=spec["title"],
            link=entity.url,
            objective=spec["objective"],
            description=spec["objective"] + " [Dato de ejemplo para demostrar la herramienta; "
            "ejecute 'Actualizar ahora' sobre la entidad para reemplazarlo con información real.]",
            opening_date_text=today.isoformat(),
            deadline_date_text=deadline.strftime("%d/%m/%Y"),
            deadline_date=deadline,
            amount_text=spec["amount_text"],
            amount_value=spec["amount_value"],
            amount_currency=spec["amount_currency"],
            scope=entity.scope,
            sdg_list=spec["sdg"],
            theme_keywords="",
            university_eligibility=spec["eligibility"],
            university_eligibility_note=spec["eligibility_note"],
            status="Vigente",
        )
        db.add(call)
        created += 1
    db.commit()
    return created


def run_seed(db: Session) -> None:
    seed_entities_if_empty(db)
    seed_demo_calls_if_empty(db)


__all__ = ["run_seed", "seed_entities_if_empty", "seed_demo_calls_if_empty"]
