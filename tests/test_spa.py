"""Tests del servido del frontend desde el backend."""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.spa import mount_spa


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>morfeo</html>", encoding="utf-8")
    (tmp_path / "manifest.webmanifest").write_text("{}", encoding="utf-8")
    (tmp_path / "assets" / "index-abc.js").write_text("console.log(1)", encoding="utf-8")
    return tmp_path


@pytest.fixture
def spa_client(dist: Path) -> TestClient:
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    assert mount_spa(app, dist)
    return TestClient(app)


def test_sin_build_no_monta_nada_y_no_revienta(tmp_path: Path):
    """Que falte un `npm run build` no puede impedir arrancar la API."""
    assert mount_spa(FastAPI(), tmp_path) is False


def test_sirve_el_index_en_la_raiz(spa_client: TestClient):
    resp = spa_client.get("/")
    assert resp.status_code == 200
    assert "morfeo" in resp.text


def test_una_ruta_de_cliente_devuelve_el_index(spa_client: TestClient):
    """Entrar directo en /historial o recargar ahí tiene que dar el index: el router
    del navegador hace el resto. Un 404 aquí rompe recargar la página."""
    resp = spa_client.get("/historial")
    assert resp.status_code == 200
    assert "morfeo" in resp.text


def test_los_ficheros_reales_se_sirven_tal_cual(spa_client: TestClient):
    assert spa_client.get("/manifest.webmanifest").status_code == 200
    assert spa_client.get("/assets/index-abc.js").text == "console.log(1)"


def test_la_api_sigue_mandando_sobre_el_comodin(spa_client: TestClient):
    assert spa_client.get("/api/ping").json() == {"ok": True}


def test_una_ruta_de_api_inexistente_es_404_y_no_el_index(spa_client: TestClient):
    """Si /api/loquesea devolviera el index, el cliente recibiría HTML donde espera
    JSON y el error saldría como un fallo de parseo incomprensible."""
    resp = spa_client.get("/api/no-existe")
    assert resp.status_code == 404
    assert "morfeo" not in resp.text


def test_no_se_puede_salir_del_directorio_del_build(spa_client: TestClient, dist: Path):
    (dist.parent / "secreto.txt").write_text("no", encoding="utf-8")
    resp = spa_client.get("/../secreto.txt")
    assert "no" not in resp.text


def test_el_index_no_se_cachea(spa_client: TestClient):
    """Apunta a assets con hash: un index cacheado pide ficheros que ya no existen."""
    assert spa_client.get("/").headers["cache-control"] == "no-cache"
