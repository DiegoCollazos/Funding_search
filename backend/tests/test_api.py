def test_stats_endpoint_reports_seeded_data(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_entities"] > 0


def test_list_entities_seeded(client):
    resp = client.get("/api/entities")
    assert resp.status_code == 200
    entities = resp.json()
    names = [e["name"] for e in entities]
    assert any("MinCiencias" in n for n in names)
    assert any("European Commission" in n for n in names)


def test_create_update_delete_entity(client):
    payload = {
        "name": "Entidad de prueba automatizada",
        "url": "https://example.org/convocatorias",
        "scope": "Nacional",
        "country": "Colombia",
        "entity_type": "Fundación",
        "adapter": "generic",
        "schedule_frequency": "manual",
        "active": True,
    }
    create_resp = client.post("/api/entities", json=payload)
    assert create_resp.status_code == 201
    entity = create_resp.json()
    entity_id = entity["id"]
    assert entity["slug"]

    update_resp = client.put(f"/api/entities/{entity_id}", json={"country": "Colombia (verificado)"})
    assert update_resp.status_code == 200
    assert update_resp.json()["country"] == "Colombia (verificado)"

    delete_resp = client.delete(f"/api/entities/{entity_id}")
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/api/entities/{entity_id}")
    assert get_resp.status_code == 404


def test_search_calls_filters_by_scope(client):
    resp = client.get("/api/calls/search", params={"scope": "Nacional"})
    assert resp.status_code == 200
    for call in resp.json():
        assert call["scope"] == "Nacional"


def test_search_calls_only_open_excludes_closed(client):
    resp = client.get("/api/calls/search", params={"only_open": True})
    assert resp.status_code == 200
    for call in resp.json():
        assert call["status"] != "Cerrada"


def test_identify_requires_url_or_text(client):
    resp = client.post("/api/identify", json={})
    assert resp.status_code == 400


def test_identify_from_pasted_text(client):
    text = (
        "Convocatoria MinCiencias. Objetivo: fortalecer capacidades de investigación. "
        "Podrán participar universidades públicas como ejecutoras. "
        "Fecha de cierre: 15 de diciembre de 2026. Monto a financiar: hasta $500.000.000 COP."
    )
    resp = client.post("/api/identify", json={"text": text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["scope"] == "Nacional"
    assert "diciembre de 2026" in data["deadline_date_text"]
    assert data["university_eligibility"] == "Sí (ejecutora)"
