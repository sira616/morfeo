"""El simulador: responder «¿y si...?» sin dejar rastro.

La regla que estos tests protegen es una sola y es la que puede estropear datos: una
simulación **no se guarda nunca**. Si se guardara, el histórico se llenaría de noches
que nadie vivió y dejaría de servir para lo único que existe, que es comprobar
después si el motor acertaba.
"""
from datetime import time

import pytest

from app.domain.bedtime import DaySignals
from app.schemas.sleep import SimulationIn
from app.services.sleep_service import apply_overrides
from tests.conftest import auth_headers


@pytest.fixture
def auth(client):
    return auth_headers(client)


def tonight(client, auth, **params):
    resp = client.get("/api/bedtime/tonight", params=params, headers=auth)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_quitar_los_cafes_adelanta_la_hora(client, auth):
    """El caso que da sentido al simulador: ver moverse la hora al quitar el café."""
    client.put(
        "/api/checkin",
        json={"coffees": 4, "last_caffeine": "19:00:00"},
        headers=auth,
    )
    con_cafe = tonight(client, auth)
    sin_cafe = tonight(client, auth, coffees=0)

    # Cuatro cafés a las siete caen dentro de la ventana de 12 h, así que penalizan
    # conciliación. Quitarlos la devuelve a la de base.
    assert sin_cafe["onset_latency_minutes"] < con_cafe["onset_latency_minutes"]


def test_simular_la_siesta_mueve_el_objetivo(client, auth):
    sin_siesta = tonight(client, auth, nap_minutes=0)
    con_siesta = tonight(client, auth, nap_minutes=60)
    # La siesta descuenta a la mitad: 60 min de siesta, 30 menos de objetivo.
    assert con_siesta["target_sleep_minutes"] == sin_siesta["target_sleep_minutes"] - 30


def test_el_ejercicio_tardio_e_intenso_aparece_como_nota(client, auth):
    """La hora de fin se calcula a partir de la recomendación real, no a ojo.

    La regla es «menos de una hora antes de acostarte», así que una hora fija en el
    test solo la dispara si la recomendación de ese día cae donde el que lo escribió
    supuso. Media hora antes de la hora recomendada la dispara siempre.
    """
    real = tonight(client, auth)
    hora, minuto = (int(x) for x in real["bedtime"].split(":")[:2])
    fin = f"{(hora * 60 + minuto - 30) // 60 % 24:02d}:{(hora * 60 + minuto - 30) % 60:02d}:00"

    simulado = tonight(
        client,
        auth,
        exercise_minutes=60,
        exercise_intensity="hard",
        exercise_end=fin,
    )
    assert any(fin[:5] in nota for nota in simulado["notes"]), simulado["notes"]


def test_ninguna_simulacion_se_guarda(client, auth):
    """Ni la hora de despertar ni el resto de señales."""
    real = tonight(client, auth)
    tonight(client, auth, coffees=0, nap_minutes=120, wake_target="05:00:00")

    guardado = client.get("/api/bedtime/history", headers=auth).json()[0]
    assert guardado["wake_target"] == real["wake_target"]
    assert guardado["bedtime"] == real["bedtime"]
    assert guardado["target_sleep_minutes"] == real["target_sleep_minutes"]


def test_sin_parametros_si_se_guarda(client, auth):
    """El otro lado de la regla: la del día tiene que congelarse igual que antes."""
    real = tonight(client, auth)
    guardado = client.get("/api/bedtime/history", headers=auth).json()[0]
    assert guardado["bedtime"] == real["bedtime"]


def test_un_parametro_mal_escrito_no_se_traga_en_silencio(client, auth):
    """Un simulador que ignora lo que no entiende parece roto sin decir por qué."""
    resp = client.get("/api/bedtime/tonight?cafes=3", headers=auth)
    assert resp.status_code == 422


def test_los_topes_de_cordura_siguen_puestos(client, auth):
    assert client.get("/api/bedtime/tonight?coffees=99", headers=auth).status_code == 422
    assert client.get("/api/bedtime/tonight?nap_minutes=-1", headers=auth).status_code == 422


# --- apply_overrides: las dos reglas que no son obvias ------------------------------


def test_cero_cafes_borra_tambien_la_hora_del_ultimo():
    """Si no, quitar todos los cafés seguiría penalizando y el cambio no haría nada.

    El motor lee «hay hora de café pero no sé cuántos» como dosis media, así que dejar
    la hora puesta con `coffees=0` es dejar la penalización puesta.
    """
    hoy = DaySignals(coffees=4, last_caffeine=time(19, 0))
    simulado = apply_overrides(hoy, SimulationIn(coffees=0))
    assert simulado.coffees == 0
    assert simulado.last_caffeine is None


def test_se_puede_simular_otra_hora_de_cafe_manteniendo_el_numero():
    hoy = DaySignals(coffees=3, last_caffeine=time(19, 0))
    simulado = apply_overrides(hoy, SimulationIn(last_caffeine=time(10, 0)))
    assert simulado.coffees == 3
    assert simulado.last_caffeine == time(10, 0)


def test_cero_ejercicio_apaga_intensidad_y_hora():
    hoy = DaySignals(exercise_minutes=90, exercise_intensity="hard", exercise_end=time(22, 0))
    simulado = apply_overrides(hoy, SimulationIn(exercise_minutes=0))
    assert simulado.exercise_intensity == "none"
    assert simulado.exercise_end is None


def test_cero_minutos_gana_a_una_intensidad_contradictoria():
    """Entrada que se contradice: manda la parte más concreta, «no hubo»."""
    hoy = DaySignals(exercise_minutes=90, exercise_intensity="hard")
    simulado = apply_overrides(hoy, SimulationIn(exercise_minutes=0, exercise_intensity="hard"))
    assert simulado.exercise_intensity == "none"


def test_lo_que_no_se_simula_se_queda_como_esta():
    hoy = DaySignals(coffees=2, nap_minutes=30, mood=4, sleep_debt_minutes=120)
    simulado = apply_overrides(hoy, SimulationIn(coffees=0))
    assert simulado.nap_minutes == 30
    assert simulado.mood == 4
    assert simulado.sleep_debt_minutes == 120


def test_una_simulacion_vacia_no_toca_nada():
    hoy = DaySignals(coffees=2, last_caffeine=time(18, 0))
    assert apply_overrides(hoy, SimulationIn()) is hoy
    assert SimulationIn().active is False
    assert SimulationIn(coffees=0).active is True
