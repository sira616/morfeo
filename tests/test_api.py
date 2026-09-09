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


def test_los_checkins_recientes_salen_en_orden_ascendente(client, auth):
    """Mismo orden que /api/sleep/nights: dos listas que se pintan juntas y se leen al
    revés la una de la otra son un error esperando a pasar."""
    hoy = date.today()
    for i in (3, 1, 2):
        client.put(
            "/api/checkin",
            json={"day": (hoy - timedelta(days=i)).isoformat(), "mood": i, "coffees": i},
            headers=auth,
        )

    dias = [c["day"] for c in client.get("/api/checkin/recent?days=7", headers=auth).json()]
    assert dias == sorted(dias)


def test_los_checkins_recientes_no_exponen_lo_escrito(client, auth):
    """Esta ruta alimenta un resumen de la portada; las notas no pintan nada ahí."""
    client.put(
        "/api/checkin",
        json={"day": date.today().isoformat(), "notes": "algo privado", "mood": 4},
        headers=auth,
    )
    cuerpo = client.get("/api/checkin/recent", headers=auth).json()
    assert cuerpo
    assert "notes" not in cuerpo[0]
    assert "algo privado" not in str(cuerpo)


def test_los_checkins_recientes_son_solo_tuyos(client, auth):
    otra = auth_headers(client)
    client.put("/api/checkin", json={"mood": 5}, headers=otra)
    mias = auth_headers(client)
    assert client.get("/api/checkin/recent", headers=mias).json() == []


def test_la_hora_del_checkin_manda_pero_se_dice_de_donde_sale(client, auth):
    """Sin contarlo, cambiar la hora en el perfil no hacía nada y parecía un cuelgue."""
    client.patch("/api/me", json={"default_wake_time": "10:00:00"}, headers=auth)
    rec = client.get("/api/bedtime/tonight", headers=auth).json()
    assert rec["wake_target"] == "10:00:00"
    assert rec["wake_target_source"] == "perfil"

    client.put("/api/checkin", json={"wake_target": "08:30:00"}, headers=auth)
    rec = client.get("/api/bedtime/tonight", headers=auth).json()
    assert rec["wake_target"] == "08:30:00"
    assert rec["wake_target_source"] == "checkin"


def test_se_puede_borrar_la_hora_del_checkin(client, auth):
    """Antes era imposible: upsert_checkin ignoraba los nulos, así que la hora se
    quedaba mandando sobre el perfil para siempre."""
    client.patch("/api/me", json={"default_wake_time": "09:15:00"}, headers=auth)
    client.put("/api/checkin", json={"wake_target": "06:00:00"}, headers=auth)
    assert client.get("/api/bedtime/tonight", headers=auth).json()["wake_target"] == "06:00:00"

    client.put("/api/checkin", json={"wake_target": None}, headers=auth)
    rec = client.get("/api/bedtime/tonight", headers=auth).json()
    assert rec["wake_target"] == "09:15:00"
    assert rec["wake_target_source"] == "perfil"


def test_no_mandar_un_campo_no_lo_borra(client, auth):
    """La otra mitad de lo mismo: `exclude_unset` distingue "no lo mando" de "ponlo a
    null", y el extractor del LLM depende de esa diferencia."""
    client.put("/api/checkin", json={"mood": 4, "coffees": 3}, headers=auth)
    client.put("/api/checkin", json={"coffees": 1}, headers=auth)

    recientes = client.get("/api/checkin/recent", headers=auth).json()
    hoy = recientes[-1]
    assert hoy["mood"] == 4
    assert hoy["coffees"] == 1


def test_las_marcas_de_tiempo_del_panel_llevan_zona(client, monkeypatch):
    """SQLite guarda UTC sin tzinfo. Sin la zona, el navegador lo lee como hora local
    y el panel enseñaba todo dos horas atrasado."""
    import uuid

    from app.core.config import settings

    username = f"admin{uuid.uuid4().hex[:10]}"
    monkeypatch.setattr(settings, "ADMIN_USERNAMES", [username])
    admin = auth_headers(client, username)

    users = client.get("/api/dev/users", headers=admin).json()
    detalle = client.get(f"/api/dev/users/{users[0]['id']}", headers=admin).json()

    assert detalle["events"], "el alta ya deja un evento"
    marca = detalle["events"][0]["at"]
    assert marca.endswith("+00:00") or marca.endswith("Z"), marca


def test_la_deuda_viaja_con_la_recomendacion_y_lleva_su_plazo(client, auth):
    """En la portada la deuda no puede ir sola: un número creciendo sin plazo al lado,
    justo antes de dormir, es ansiedad y no información."""
    hoy = date.today()
    nights = [
        {
            "night_of": (hoy - timedelta(days=i)).isoformat(),
            "total_sleep_minutes": 400,
            "time_in_bed_minutes": 460,
        }
        for i in range(1, 8)
    ]
    client.post("/api/sleep/nights", json={"nights": nights}, headers=auth)

    deuda = client.get("/api/bedtime/tonight", headers=auth).json()["sleep_debt"]
    # Siete noches de 400 min contra 480 de necesidad: 560 min de déficit.
    assert deuda["minutes"] == 560
    assert deuda["level"] == "alta"
    assert deuda["nights_with_deficit"] == 7
    # Las siete noches malas tienen que salir de la ventana para que deje de contar.
    assert deuda["nights_to_clear"] == 7
    # Y es el mismo número del factor que mueve la hora de esta noche.
    rec = client.get("/api/bedtime/tonight", headers=auth).json()
    factor = next(f for f in rec["factors"] if f["label"] == "Deuda de sueño")
    assert deuda["tonight_recovery_minutes"] == factor["minutes"]


def test_el_historico_no_inventa_la_deuda_de_aquel_dia(client, auth):
    """No se congeló con la recomendación, así que va a null. Recalcularla hoy daría
    un número que aquel día nadie vio."""
    client.get("/api/bedtime/tonight", headers=auth)
    historico = client.get("/api/bedtime/history?limit=1", headers=auth).json()
    assert historico[0]["sleep_debt"] is None


def _semana(client, auth, hoy: date) -> None:
    nights = [
        {
            "night_of": (hoy - timedelta(days=i)).isoformat(),
            "total_sleep_minutes": 420,
            "time_in_bed_minutes": 470,
            "bed_at": f"{(hoy - timedelta(days=i)).isoformat()}T23:30:00",
        }
        for i in range(7)
    ]
    client.post("/api/sleep/nights", json={"nights": nights}, headers=auth)


def test_el_informe_semanal_habla_de_las_ultimas_siete_noches_cualquier_dia(client, auth):
    """La ventana es móvil y no la semana del calendario: si solo cuadrara los
    domingos habría que acordarse de abrirlo el domingo."""
    hoy = date.today()
    _semana(client, auth, hoy)
    client.get("/api/bedtime/tonight", headers=auth)  # congela la de hoy

    informe = client.get("/api/insights/weekly", headers=auth).json()
    assert informe["start"] == (hoy - timedelta(days=6)).isoformat()
    assert informe["end"] == hoy.isoformat()
    assert informe["current"]["nights"] == 7
    assert informe["current"]["mean_sleep_minutes"] == 420
    assert len(informe["nights"]) == 7
    assert informe["highlights"]

    # Solo hoy tiene recomendación guardada, así que solo de hoy se puede decir si se
    # cumplió la ventana. Las demás quedan en hueco, no en "no cumplida".
    assert informe["window_measured"] == 1
    assert sum(1 for n in informe["nights"] if n["in_window"] is not None) == 1


def test_sin_semana_anterior_las_comparaciones_van_a_null(client, auth):
    _semana(client, auth, date.today())
    informe = client.get("/api/insights/weekly", headers=auth).json()
    assert informe["previous"]["mean_sleep_minutes"] is None
    assert informe["sleep_delta_minutes"] is None
    assert informe["midpoint_shift_minutes"] is None


def test_el_offset_retrocede_semanas_enteras(client, auth):
    hoy = date.today()
    _semana(client, auth, hoy)
    anterior = client.get("/api/insights/weekly?offset=1", headers=auth).json()
    assert anterior["end"] == (hoy - timedelta(days=7)).isoformat()
    assert anterior["current"]["nights"] == 0
    # Y la anterior a esa tampoco: el informe no se inventa una comparación.
    assert anterior["previous"]["nights"] == 0
