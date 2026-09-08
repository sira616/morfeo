"""Tests de extremo a extremo sobre la API. Supabase Auth está doblado en conftest,
así que corren sin red y sin claves."""
import json
from datetime import date, timedelta

import pytest

from tests.conftest import auth_headers


@pytest.fixture
def auth(client):
    return auth_headers(client)


def test_health():
    from app.main import app  # noqa: F401  — importable sin arrancar servidor

    assert True


def test_el_perfil_recien_creado_trae_los_valores_por_defecto(client, auth):
    me = client.get("/api/me", headers=auth).json()
    assert me["emailVerified"] is True  # sin email no hay nada que verificar
    assert me["defaultWakeTime"] == "07:00:00"
    assert me["sleepNeedMinutes"] == 480
    assert me["onboardingDone"] is False


def test_patch_parcial_no_borra_lo_demas(client, auth):
    client.patch("/api/me", json={"default_wake_time": "06:30:00"}, headers=auth)
    me = client.patch("/api/me", json={"sleep_need_minutes": 450}, headers=auth).json()
    assert me["defaultWakeTime"] == "06:30:00"
    assert me["sleepNeedMinutes"] == 450


def test_sin_credencial_responde_401_y_no_403(client):
    """El frontend distingue ambos códigos para decidir si refresca o manda al login."""
    assert client.get("/api/bedtime/tonight").status_code == 401


def test_alta_de_noches_y_recomendacion(client, auth):
    hoy = date.today()
    nights = [
        {
            "night_of": (hoy - timedelta(days=i)).isoformat(),
            "total_sleep_minutes": 400,
            "time_in_bed_minutes": 460,
            "onset_latency_minutes": 25,
        }
        for i in range(1, 11)
    ]
    resp = client.post("/api/sleep/nights", json={"nights": nights}, headers=auth)
    assert resp.status_code == 201
    assert resp.json()["written"] == 10

    rec = client.get("/api/bedtime/tonight", headers=auth).json()
    # 10 noches de 400 min contra una necesidad de 480 son 800 min de deuda: el motor
    # recupera a plazos y con tope, así que el objetivo sube 60 min y no 800.
    assert rec["target_sleep_minutes"] == 540
    assert rec["confidence"] == "media"
    assert rec["onset_latency_minutes"] == 25
    assert any(f["label"] == "Deuda de sueño" for f in rec["factors"])


def test_reenviar_la_misma_noche_no_duplica(client, auth):
    noche = {
        "night_of": date.today().isoformat(),
        "total_sleep_minutes": 400,
        "time_in_bed_minutes": 460,
    }
    client.post("/api/sleep/nights", json={"nights": [noche]}, headers=auth)
    client.post("/api/sleep/nights", json={"nights": [{**noche, "total_sleep_minutes": 420}]}, headers=auth)
    nights = client.get("/api/sleep/nights?days=2", headers=auth).json()
    de_hoy = [n for n in nights if n["night_of"] == date.today().isoformat()]
    assert len(de_hoy) == 1
    assert de_hoy[0]["total_sleep_minutes"] == 420


def test_dormir_mas_que_estar_en_la_cama_es_422(client, auth):
    resp = client.post(
        "/api/sleep/nights",
        json={
            "nights": [
                {
                    "night_of": date.today().isoformat(),
                    "total_sleep_minutes": 500,
                    "time_in_bed_minutes": 400,
                }
            ]
        },
        headers=auth,
    )
    assert resp.status_code == 422


def test_importacion_con_formato_roto_explica_la_fila(client, auth):
    resp = client.post(
        "/api/sleep/import",
        json={"content": json.dumps([{"night_of": "ayer", "total_sleep_minutes": 1, "time_in_bed_minutes": 2}])},
        headers=auth,
    )
    assert resp.status_code == 422
    assert "Fila 1" in resp.json()["detail"]


def test_el_checkin_alimenta_la_recomendacion(client, auth):
    """La siesta declarada tiene que mover la hora: si no, el check-in es decorativo."""
    antes = client.get("/api/bedtime/tonight", headers=auth).json()
    client.put("/api/checkin", json={"nap_minutes": 60, "mood": 4}, headers=auth)
    despues = client.get("/api/bedtime/tonight", headers=auth).json()
    assert despues["target_sleep_minutes"] == antes["target_sleep_minutes"] - 30


def test_wake_target_simula_sin_guardar(client, auth):
    real = client.get("/api/bedtime/tonight", headers=auth).json()
    simulado = client.get("/api/bedtime/tonight?wake_target=05:00:00", headers=auth).json()
    assert simulado["wake_target"] == "05:00:00"

    guardado = client.get("/api/bedtime/history", headers=auth).json()[0]
    assert guardado["wake_target"] == real["wake_target"]


def test_marcar_seguida_una_recomendacion_inexistente_es_404(client, auth):
    resp = client.patch("/api/bedtime/2020-01-01/followed", json={"followed": True}, headers=auth)
    assert resp.status_code == 404


def test_no_se_ven_las_noches_de_otra_persona(client):
    otra = auth_headers(client)
    client.post(
        "/api/sleep/nights",
        json={
            "nights": [
                {
                    "night_of": "2026-01-01",
                    "total_sleep_minutes": 400,
                    "time_in_bed_minutes": 460,
                }
            ]
        },
        headers=otra,
    )
    mias = auth_headers(client)
    nights = client.get("/api/sleep/nights?days=365", headers=mias).json()
    assert nights == []
