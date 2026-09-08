"""Tests del corpus de consejos y de su selección."""
from datetime import date, timedelta

import pytest

from app.content.sleep_tips import SIGNAL_ALCOHOL, SIGNAL_CAFFEINE_LATE, TIPS, TIPS_BY_ID
from app.services.tips_service import MAX_RELEVANT, TIPS_PER_DAY, pick


def test_los_identificadores_no_se_repiten():
    assert len(TIPS_BY_ID) == len(TIPS)


def test_todos_declaran_evidencia_y_fuente():
    """Enseñar el nivel de evidencia es la decisión de producto que separa esto de una
    lista de tópicos. Un consejo sin fuente no debería poder colarse."""
    for tip in TIPS:
        assert tip.evidence in ("alta", "media", "baja"), tip.id
        assert tip.source.strip(), tip.id
        assert len(tip.body) > 60, tip.id


def test_hay_consejos_de_sobra_para_no_repetir_en_un_dia():
    assert len(TIPS) >= TIPS_PER_DAY * 4


def test_devuelve_cinco_sin_repetir():
    elegidos = pick(set(), seed="usuario:2026-09-08")
    assert len(elegidos) == TIPS_PER_DAY
    assert len({t.id for t in elegidos}) == TIPS_PER_DAY


def test_la_misma_semilla_da_los_mismos_consejos():
    """Estabilidad durante el día: unos consejos que bailan al recargar no se leen."""
    a = pick(set(), seed="usuario:2026-09-08")
    b = pick(set(), seed="usuario:2026-09-08")
    assert [t.id for t in a] == [t.id for t in b]


def test_cambian_de_un_dia_a_otro():
    a = pick(set(), seed="usuario:2026-09-08")
    b = pick(set(), seed="usuario:2026-09-09")
    assert [t.id for t in a] != [t.id for t in b]


def test_las_senales_activas_mandan_al_frente():
    elegidos = pick({SIGNAL_CAFFEINE_LATE, SIGNAL_ALCOHOL}, seed="usuario:2026-09-08")
    relevantes = [t for t in elegidos if t.applies_when in (SIGNAL_CAFFEINE_LATE, SIGNAL_ALCOHOL)]
    assert len(relevantes) >= 2


def test_lo_relevante_tiene_tope():
    """Cinco consejos sobre la cafeína el mismo día serían insoportables.

    El relleno puede traer consejos condicionales que hoy no aplican, y está bien: se
    leen igual como consejo general. Lo que no puede pasar es que la selección entera
    gire alrededor de las señales de hoy.
    """
    activas = {SIGNAL_CAFFEINE_LATE, SIGNAL_ALCOHOL}
    elegidos = pick(activas, seed="usuario:2026-09-08")
    disparados = [t for t in elegidos if t.applies_when in activas]
    assert len(disparados) <= MAX_RELEVANT
    assert len(elegidos) - len(disparados) >= TIPS_PER_DAY - MAX_RELEVANT


@pytest.fixture
def auth_con_cafe(client):
    import uuid

    email = f"{uuid.uuid4()}@example.com"
    client.post("/api/auth/register", json={"email": email, "password": "contrasena-larga-123"})
    token = client.post(
        "/api/auth/login", json={"email": email, "password": "contrasena-larga-123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/api/checkin", json={"last_caffeine": "19:00:00", "alcohol": True}, headers=headers)
    return headers


def test_la_ruta_marca_cuales_salen_por_una_senal(client, auth_con_cafe):
    body = client.get("/api/tips/today", headers=auth_con_cafe).json()
    assert len(body["tips"]) == TIPS_PER_DAY
    assert SIGNAL_CAFFEINE_LATE in body["signals"]
    assert any(t["relevant"] for t in body["tips"])


def test_insights_sin_datos_no_inventa_metricas(client):
    import uuid

    email = f"{uuid.uuid4()}@example.com"
    client.post("/api/auth/register", json={"email": email, "password": "contrasena-larga-123"})
    token = client.post(
        "/api/auth/login", json={"email": email, "password": "contrasena-larga-123"}
    ).json()["access_token"]
    body = client.get("/api/insights", headers={"Authorization": f"Bearer {token}"}).json()

    # Cuentas nuevas: nulo, nunca un cero que se leería como "horario irregular".
    assert body["regularity"] is None
    assert body["social_jetlag"] is None
    assert body["adherence"]["streak"] == 0
    assert body["heatmap"] == []


def test_insights_calcula_regularidad_con_horas_reales(client):
    import uuid

    email = f"{uuid.uuid4()}@example.com"
    client.post("/api/auth/register", json={"email": email, "password": "contrasena-larga-123"})
    token = client.post(
        "/api/auth/login", json={"email": email, "password": "contrasena-larga-123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    hoy = date.today()
    nights = []
    for i in range(1, 15):
        noche = hoy - timedelta(days=i)
        nights.append(
            {
                "night_of": noche.isoformat(),
                "total_sleep_minutes": 420,
                "time_in_bed_minutes": 470,
                "sleep_start": f"{noche.isoformat()}T23:00:00",
                "sleep_end": f"{(noche + timedelta(days=1)).isoformat()}T07:00:00",
            }
        )
    client.post("/api/sleep/nights", json={"nights": nights}, headers=headers)

    body = client.get("/api/insights", headers=headers).json()
    assert body["regularity"]["score"] == 100
    assert body["regularity"]["nights"] == 14
    assert len(body["heatmap"]) == 14
