import os
import tempfile

import pytest

# La URL de base de datos se lee al importar backend.database, así que debe
# fijarse ANTES de importar cualquier módulo de la app (evita tocar la base
# de datos real de desarrollo al correr los tests).
_tmp_dir = tempfile.mkdtemp(prefix="funding_search_test_")
os.environ["FUNDING_SEARCH_DB_URL"] = f"sqlite:///{os.path.join(_tmp_dir, 'test.db')}"

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
