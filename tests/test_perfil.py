"""Personalización del perfil: avatar, horario de finde, cronotipo y objetivo.

El grueso es cosmético y se prueba solo (que guarde, que valide, que se pueda vaciar).
Lo que de verdad importa aquí es el horario de finde, porque es lo único que toca el
cálculo: la noche cuya mañana cae en sábado o domingo tiene que usar esa hora.
"""
from datetime import date, time

import pytest

from app.services.sleep_service import resolve_wake_target
from tests.conftest import PASSWORD, auth_headers, register


@pytest.fixture
def auth(client):
    return auth_headers(client)


def me(client, auth):
    return client.get("/api/me", headers=auth).json()


def test_los_campos_nuevos_salen_con_sus_defaults(client, auth):
    cuerpo = me(client, auth)
    assert cuerpo["avatarColor"] == "#4fd6a0"
    assert cuerpo["chronotype"] == "intermedio"
    assert cuerpo["weekendWakeTime"] is None
    assert cuerpo["avatarEmoji"] is None
    assert cuerpo["goal"] is None


def test_guardar_identidad_y_objetivo(client, auth):
    r = client.patch("/api/me", headers=auth, json={
        "display_name": "Sira", "avatar_color": "#6c5ce7",
        "avatar_emoji": "🌙", "goal": "Dormir mejor antes de las oposiciones",
        "chronotype": "buho",
    })
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["displayName"] == "Sira"
    assert cuerpo["avatarColor"] == "#6c5ce7"
    assert cuerpo["avatarEmoji"] == "🌙"
    assert cuerpo["goal"].startswith("Dormir mejor")
    assert cuerpo["chronotype"] == "buho"


def test_un_color_fuera_de_la_paleta_se_rechaza(client, auth):
    # Un hex libre podía ser blanco sobre blanco: el color va contra una lista cerrada.
    r = client.patch("/api/me", headers=auth, json={"avatar_color": "#ffffff"})
    assert r.status_code == 422


def test_un_cronotipo_inventado_se_rechaza(client, auth):
    assert client.patch("/api/me", headers=auth, json={"chronotype": "murcielago"}).status_code == 422


def test_el_objetivo_tiene_tope(client, auth):
    assert client.patch("/api/me", headers=auth, json={"goal": "x" * 200}).status_code == 422


def test_el_horario_de_finde_se_puede_poner_y_vaciar(client, auth):
    puesto = client.patch("/api/me", headers=auth, json={"weekend_wake_time": "09:30:00"}).json()
    assert puesto["weekendWakeTime"] == "09:30:00"

    # Vaciarlo con null es "vuelve a usar el de diario", no "no lo toques". Sin eso, una
    # vez puesto el horario de finde no habría forma de quitarlo.
    vaciado = client.patch("/api/me", headers=auth, json={"weekend_wake_time": None}).json()
    assert vaciado["weekendWakeTime"] is None


def test_null_no_borra_lo_que_no_es_vaciable(client, auth):
    """Mandar la hora de despertar a null no la borra: para casi todo, null es "ignora"."""
    antes = me(client, auth)["defaultWakeTime"]
    despues = client.patch("/api/me", headers=auth, json={"default_wake_time": None}).json()
    assert despues["defaultWakeTime"] == antes


# --- Lo que toca el motor: el horario de finde ------------------------------------


def test_la_noche_del_viernes_usa_la_hora_del_finde(client):
    """Viernes despierta en sábado: ya es finde, aunque el viernes sea día laborable."""
    from sqlalchemy import select
    from app.core.database import SessionLocal
    from app.models.user import User

    datos = register(client)
    with SessionLocal() as s:
        u = s.scalar(select(User).where(User.username == datos["user"]["username"]))
        u.default_wake_time = time(7, 0)
        u.weekend_wake_time = time(9, 30)
        s.commit()

        viernes = date(2026, 9, 11)   # su mañana siguiente es sábado 12
        sabado = date(2026, 9, 12)    # despierta en domingo 13
        domingo = date(2026, 9, 13)   # despierta en lunes 14 (laborable)
        lunes = date(2026, 9, 14)     # despierta en martes (laborable)

        assert resolve_wake_target(s, u, viernes, None) == (time(9, 30), "perfil")
        assert resolve_wake_target(s, u, sabado, None) == (time(9, 30), "perfil")
        assert resolve_wake_target(s, u, domingo, None) == (time(7, 0), "perfil")
        assert resolve_wake_target(s, u, lunes, None) == (time(7, 0), "perfil")


def test_sin_hora_de_finde_todo_usa_la_de_diario(client):
    from sqlalchemy import select
    from app.core.database import SessionLocal
    from app.models.user import User

    datos = register(client)
    with SessionLocal() as s:
        u = s.scalar(select(User).where(User.username == datos["user"]["username"]))
        u.default_wake_time = time(6, 30)
        u.weekend_wake_time = None
        s.commit()
        viernes = date(2026, 9, 11)
        assert resolve_wake_target(s, u, viernes, None) == (time(6, 30), "perfil")


def test_el_checkin_gana_al_horario_de_finde(client):
    """Un "mañana me levanto a las 6" del check-in es más específico que el finde."""
    from sqlalchemy import select
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.models.sleep import Checkin

    datos = register(client)
    with SessionLocal() as s:
        u = s.scalar(select(User).where(User.username == datos["user"]["username"]))
        u.weekend_wake_time = time(9, 30)
        s.add(Checkin(user_id=u.id, day=date(2026, 9, 11), wake_target=time(6, 0)))
        s.commit()
        hora, fuente = resolve_wake_target(s, u, date(2026, 9, 11), None)
        assert (hora, fuente) == (time(6, 0), "checkin")


def test_el_cronotipo_prioriza_su_consejo(client):
    """La promesa del perfil: elegir búho hace que salga el consejo del búho.

    No cambia el cálculo —eso sería inventarse ciencia—, solo qué consejo se prioriza.
    """
    from datetime import date as _date
    from sqlalchemy import select
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.services import tips_service

    datos = register(client)
    with SessionLocal() as s:
        u = s.scalar(select(User).where(User.username == datos["user"]["username"]))
        u.chronotype = "buho"
        s.commit()
        activas = tips_service.signals(s, u, _date(2026, 9, 14))
        assert "cronotipo_buho" in activas
        elegidos = tips_service.pick(activas, seed="x")
        assert any(t.id == "cronotipo-buho-luz-manana" for t in elegidos)


def test_el_ano_de_nacimiento_se_guarda_y_se_vacia(client, auth):
    puesto = client.patch("/api/me", headers=auth, json={"birth_year": 1995}).json()
    assert puesto["birthYear"] == 1995
    # null lo borra, como los demás campos vaciables.
    vaciado = client.patch("/api/me", headers=auth, json={"birth_year": None}).json()
    assert vaciado["birthYear"] is None


def test_un_ano_de_nacimiento_absurdo_se_rechaza(client, auth):
    assert client.patch("/api/me", headers=auth, json={"birth_year": 1700}).status_code == 422
    assert client.patch("/api/me", headers=auth, json={"birth_year": 2025}).status_code == 422
