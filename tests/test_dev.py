"""Tests del panel de /dev: quién entra, qué ve y qué no ve."""
import uuid
from datetime import date

import pytest

from app.core.config import settings
from tests.conftest import auth_headers


@pytest.fixture
def admin(client, monkeypatch):
    username = f"admin{uuid.uuid4().hex[:10]}"
    monkeypatch.setattr(settings, "ADMIN_USERNAMES", [username])
    return auth_headers(client, username)


@pytest.fixture
def normal(client):
    return auth_headers(client)


def test_quien_no_es_admin_recibe_404_y_no_403(client, normal):
    """Un 403 confirma que la ruta existe y que hay algo detrás que buscar."""
    assert client.get("/api/dev/users", headers=normal).status_code == 404


def test_sin_sesion_es_401(client):
    assert client.get("/api/dev/users").status_code == 401


def test_el_admin_ve_los_perfiles_registrados(client, admin, normal):
    users = client.get("/api/dev/users", headers=admin).json()
    assert len(users) >= 2
    assert {"username", "nights", "checkins", "recommendations", "last_seen"} <= set(users[0])


def test_el_rol_no_se_acepta_del_cliente(client, normal):
    """El flag sale de ADMIN_USERNAMES en el servidor, no de nada que mande el cliente."""
    me = client.get("/api/me", headers=normal).json()
    assert me["isAdmin"] is False

    client.patch("/api/me", json={"display_name": "x"}, headers=normal)
    assert client.get("/api/me", headers=normal).json()["isAdmin"] is False


def test_el_detalle_trae_el_registro_de_actividad(client, admin):
    headers = auth_headers(client)
    client.put("/api/checkin", json={"coffees": 2, "mood": 4}, headers=headers)
    client.post(
        "/api/sleep/nights",
        json={
            "nights": [
                {
                    "night_of": date.today().isoformat(),
                    "total_sleep_minutes": 400,
                    "time_in_bed_minutes": 460,
                }
            ]
        },
        headers=headers,
    )

    user_id = client.get("/api/me", headers=headers).json()["id"]
    detail = client.get(f"/api/dev/users/{user_id}", headers=admin).json()

    acciones = {e["action"] for e in detail["events"]}
    assert {"register", "checkin", "nights"} <= acciones
    assert detail["user"]["checkins"] == 1
    assert detail["user"]["nights"] == 1


def test_el_registro_no_guarda_lo_que_la_gente_escribe(client, admin):
    """El panel sirve para ver que la app se usa, no para leer los check-ins."""
    headers = auth_headers(client)
    client.put(
        "/api/checkin",
        json={"notes": "un secreto que no debe salir del check-in", "mood": 2},
        headers=headers,
    )

    user_id = client.get("/api/me", headers=headers).json()["id"]
    detail = client.get(f"/api/dev/users/{user_id}", headers=admin).json()

    volcado = str(detail)
    assert "secreto" not in volcado
    # Sí queda constancia de qué campos se registraron, que es el propósito.
    assert any(e["action"] == "checkin" and "notes" in (e["summary"] or "") for e in detail["events"])


def test_un_usuario_inexistente_es_404(client, admin):
    assert client.get("/api/dev/users/no-existe", headers=admin).status_code == 404


def test_el_login_ya_dice_que_eres_admin(client, monkeypatch):
    """Si el flag solo se calculara en la primera petición autenticada, la respuesta
    del login diría que no eres admin y el frontend escondería el panel."""
    username = f"admin{uuid.uuid4().hex[:10]}"
    monkeypatch.setattr(settings, "ADMIN_USERNAMES", [username])

    alta = client.post(
        "/api/auth/register", json={"username": username, "password": "ContrasenaLarga123"}
    ).json()
    assert alta["user"]["isAdmin"] is True

    entrada = client.post(
        "/api/auth/login", json={"login": username, "password": "ContrasenaLarga123"}
    ).json()
    assert entrada["user"]["isAdmin"] is True
