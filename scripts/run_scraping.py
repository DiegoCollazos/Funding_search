#!/usr/bin/env python3
"""CLI de scraping para la variante estática (GitHub Pages + GitHub Actions).

A diferencia del backend con FastAPI/SQLite, esta variante no tiene un
servidor corriendo de forma continua: un GitHub Action ejecuta este script
por cron (o al disparar el workflow manualmente desde la propia página, vía
la API de GitHub) y el resultado —``docs/data/entities.json`` y
``docs/data/calls.json``— se commitea de vuelta al repositorio. GitHub Pages
sirve esos archivos como datos estáticos que la interfaz filtra en el
navegador.

Reutiliza exactamente la misma lógica de scraping y extracción del backend
(``backend/scraping/*``), que ya era independiente de la base de datos salvo
por el propio ``runner.py`` (ver el pequeño ajuste en ``enrich_raw_call`` para
aceptar el alcance como string en vez de un objeto ORM).

Uso:
    python scripts/run_scraping.py                  # todas las entidades activas
    python scripts/run_scraping.py --only-due          # solo las que ya cumplieron su frecuencia (uso en cron)
    python scripts/run_scraping.py --entity-id minciencias-convocatorias   # una sola (uso desde "Actualizar ahora")
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.scraping.adapters.registry import get_adapter  # noqa: E402
from backend.scraping.enrich import enrich_raw_call  # noqa: E402

DATA_DIR = BASE_DIR / "docs" / "data"
ENTITIES_PATH = DATA_DIR / "entities.json"
CALLS_PATH = DATA_DIR / "calls.json"

_FREQUENCY_DELTAS = {
    "diario": dt.timedelta(days=1),
    "semanal": dt.timedelta(weeks=1),
    "mensual": dt.timedelta(days=30),
}


def _load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _call_id(entity_id: str, link: str) -> str:
    digest = hashlib.sha1(f"{entity_id}|{link}".encode("utf-8")).hexdigest()[:12]
    return f"{entity_id}-{digest}"


def _is_due(entity: dict, now: dt.datetime) -> bool:
    if not entity.get("active", True) or entity.get("schedule_frequency") == "manual":
        return False
    last = entity.get("last_scraped_at")
    if not last:
        return True
    delta = _FREQUENCY_DELTAS.get(entity.get("schedule_frequency"))
    if delta is None:
        return False
    try:
        last_dt = dt.datetime.fromisoformat(last)
    except ValueError:
        return True
    return now - last_dt >= delta


def _refresh_call_status(call: dict, today: dt.date) -> None:
    deadline = call.get("deadline_date")
    if not deadline:
        call["status"] = "Por confirmar"
        return
    try:
        deadline_date = dt.date.fromisoformat(deadline)
    except ValueError:
        call["status"] = "Por confirmar"
        return
    call["status"] = "Vigente" if deadline_date >= today else "Cerrada"


def scrape_entity(entity: dict, calls_by_key: dict[tuple[str, str], dict]) -> tuple[int, int, str, str]:
    """Scrapea una entidad y actualiza ``calls_by_key`` in-place.

    Devuelve (encontradas, nuevas, estado, mensaje).
    """
    entity_ns = SimpleNamespace(
        url=entity["url"],
        scraper_config=entity.get("scraper_config") or {},
        adapter=entity.get("adapter", "generic"),
        scope=entity.get("scope", "Internacional"),
    )
    try:
        adapter = get_adapter(entity.get("adapter", "generic"))
        raw_calls = adapter(entity_ns) or []
        found = 0
        new = 0
        now_iso = dt.datetime.utcnow().isoformat()
        for raw in raw_calls:
            if not raw.get("link") or not raw.get("title"):
                continue
            found += 1
            enriched = enrich_raw_call(raw, entity["scope"])
            if isinstance(enriched.get("deadline_date"), dt.date):
                enriched["deadline_date"] = enriched["deadline_date"].isoformat()
            key = (entity["id"], enriched["link"])
            existing = calls_by_key.get(key)
            if existing:
                existing.update(enriched)
                existing["entity_id"] = entity["id"]
                existing["entity_name"] = entity["name"]
                existing["last_seen_at"] = now_iso
            else:
                new_call = {
                    "id": _call_id(entity["id"], enriched["link"]),
                    "entity_id": entity["id"],
                    "entity_name": entity["name"],
                    **enriched,
                    "first_seen_at": now_iso,
                    "last_seen_at": now_iso,
                }
                calls_by_key[key] = new_call
                new += 1
        message = f"{found} convocatoria(s) encontradas, {new} nueva(s)."
        return found, new, "ok", message
    except Exception as exc:  # noqa: BLE001 - se registra el error, no debe tumbar el resto del run
        return 0, 0, "error", str(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entity-id", default=None, help="Scrapear solo esta entidad (por id/slug)")
    parser.add_argument("--only-due", action="store_true", help="Scrapear solo entidades que ya cumplieron su frecuencia")
    args = parser.parse_args()

    entities = _load_json(ENTITIES_PATH, [])
    calls = _load_json(CALLS_PATH, [])
    calls_by_key = {(c["entity_id"], c["link"]): c for c in calls}

    now = dt.datetime.utcnow()
    today = now.date()

    if args.entity_id:
        targets = [e for e in entities if e["id"] == args.entity_id]
        if not targets:
            print(f"::error::No existe ninguna entidad con id '{args.entity_id}'", file=sys.stderr)
            sys.exit(1)
    elif args.only_due:
        targets = [e for e in entities if _is_due(e, now)]
    else:
        targets = [e for e in entities if e.get("active", True)]

    print(f"Entidades a scrapear: {len(targets)} de {len(entities)}")

    for entity in targets:
        print(f"→ {entity['name']} ({entity['id']})")
        found, new, status, message = scrape_entity(entity, calls_by_key)
        entity["last_scraped_at"] = now.isoformat()
        entity["last_status"] = status
        entity["last_message"] = message
        print(f"   {status}: {message}")

    all_calls = list(calls_by_key.values())
    for call in all_calls:
        _refresh_call_status(call, today)
    all_calls.sort(key=lambda c: (c.get("deadline_date") is None, c.get("deadline_date") or "", c.get("title", "")))

    entities.sort(key=lambda e: (e.get("scope", ""), e.get("name", "")))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _save_json(ENTITIES_PATH, entities)
    _save_json(CALLS_PATH, all_calls)
    print(f"Listo. {len(all_calls)} convocatoria(s) en total en {CALLS_PATH}.")


if __name__ == "__main__":
    main()
