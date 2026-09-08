"""Tests de la autenticación local: usuario, contraseña, JWT y confirmación de email."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.core import tokens
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.passwords import MIN_LENGTH
from app.models.auth import EmailVerification, RefreshToken
from app.models.user import User
from tests.conftest import PASSWORD, auth_headers, register


def _name() -> str:
    return f"u{uuid.uuid4().hex[:12]}"


# --- Registro -------------------------------------------------------------------


def test_una_cuenta_sin_email_nace_verificada(client):
    """No hay nada que verificar, así que no debe arrastrar un aviso eterno."""
    body = register(client)
    assert body["user"]["email"] is None
    assert body["user"]["emailVerified"] is True


def test_el_registro_ya_devuelve_la_sesion(client):
    body = register(client)
    assert body["access_token"] and body["refresh_token"]
    me = client.get("/api/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200


def test_el_usuario_no_distingue_mayusculas(client):
    name = _name()
    register(client, name.upper())
    resp = client.post("/api/auth/register", json={"username": name, "password": PASSWORD})
    assert resp.status_code == 409


@pytest.mark.parametrize("malo", ["ab", "con espacio", "-empieza-mal", "acaba-mal-", "ñandú"])
def test_nombres_de_usuario_invalidos(client, malo):
    resp = client.post("/api/auth/register", json={"username": malo, "password": PASSWORD})
    assert resp.status_code in (409, 422)


@pytest.mark.parametrize(
    "flojita", ["corta1A", "todominusculas123", "TODOMAYUSCULAS123", "SinNumerosAqui"]
)
def test_contrasenas_que_no_cumplen_la_politica(client, flojita):
    resp = client.post("/api/auth/register", json={"username": _name(), "password": flojita})
    assert resp.status_code == 422


def test_el_mensaje_de_politica_dice_que_falta(client):
    resp = client.post("/api/auth/register", json={"username": _name(), "password": "a" * 20})
    assert resp.status_code == 422
    assert "mayúscula" in resp.json()["detail"].lower()


def test_la_longitud_minima_es_la_documentada(client):
    justo = "Aa1" + "b" * (MIN_LENGTH - 3)
    assert client.post(
        "/api/auth/register", json={"username": _name(), "password": justo}
    ).status_code == 201


# --- Login ----------------------------------------------------------------------


def test_se_entra_con_el_usuario(client):
    name = _name()
    register(client, name)
    resp = client.post("/api/auth/login", json={"login": name, "password": PASSWORD})
    assert resp.status_code == 200


def test_se_entra_tambien_con_el_email_si_lo_hay(client):
    name, email = _name(), f"{uuid.uuid4().hex[:10]}@example.com"
    register(client, name, email=email)
    resp = client.post("/api/auth/login", json={"login": email, "password": PASSWORD})
    assert resp.status_code == 200


def test_usuario_inexistente_y_contrasena_mala_dan_el_mismo_mensaje(client):
    name = _name()
    register(client, name)
    mala = client.post("/api/auth/login", json={"login": name, "password": "OtraCosa123456"})
    inexistente = client.post("/api/auth/login", json={"login": _name(), "password": PASSWORD})

    assert mala.status_code == inexistente.status_code == 401
    # Distinguirlos convertiría el formulario en un buscador de cuentas.
    assert mala.json()["detail"] == inexistente.json()["detail"]


# --- Tokens ---------------------------------------------------------------------


def test_sin_credencial_es_401(client):
    assert client.get("/api/me").status_code == 401


def test_un_token_con_otra_firma_no_vale(client):
    ajeno = jwt.encode(
        {"sub": "x", "type": "access", "jti": "1", "exp": 9999999999}, "otro-secreto", "HS256"
    )
    assert client.get("/api/me", headers={"Authorization": f"Bearer {ajeno}"}).status_code == 401


def test_un_refresh_no_sirve_como_access(client):
    """Sin comprobar el `type`, un refresh duraría treinta días en vez de treinta
    minutos."""
    body = register(client)
    resp = client.get("/api/me", headers={"Authorization": f"Bearer {body['refresh_token']}"})
    assert resp.status_code == 401


def test_un_access_no_sirve_para_refrescar(client):
    body = register(client)
    resp = client.post("/api/auth/refresh", json={"refresh_token": body["access_token"]})
    assert resp.status_code == 401


def test_un_token_caducado_no_vale(client):
    body = register(client)
    user_id = client.get(
        "/api/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    ).json()["id"]
    caducado = jwt.encode(
        {
            "sub": user_id,
            "type": "access",
            "jti": "x",
            "exp": int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp()),
        },
        settings.JWT_SECRET,
        "HS256",
    )
    assert client.get("/api/me", headers={"Authorization": f"Bearer {caducado}"}).status_code == 401


def test_refrescar_rota_el_token_y_anula_el_anterior(client):
    """Sin rotación, un refresh robado sirve treinta días en paralelo a la sesión
    legítima y nadie se entera."""
    body = register(client)
    primero = body["refresh_token"]

    resp = client.post("/api/auth/refresh", json={"refresh_token": primero})
    assert resp.status_code == 200
    segundo = resp.json()["refresh_token"]
    assert segundo != primero

    assert client.post("/api/auth/refresh", json={"refresh_token": primero}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": segundo}).status_code == 200


def test_cerrar_sesion_revoca_el_refresh(client):
    body = register(client)
    assert client.post("/api/auth/logout", json={"refresh_token": body["refresh_token"]}).status_code == 204
    assert client.post(
        "/api/auth/refresh", json={"refresh_token": body["refresh_token"]}
    ).status_code == 401


def test_cerrar_una_sesion_ya_invalida_no_es_un_error(client):
    """El objetivo era que dejara de servir, y ya no sirve."""
    assert client.post("/api/auth/logout", json={"refresh_token": "basura"}).status_code == 204


def test_el_jti_guardado_no_es_el_token(client):
    """Quien lea la base de datos no se lleva credenciales usables."""
    body = register(client)
    with SessionLocal() as db:
        filas = list(db.scalars(select(RefreshToken)))
    assert filas
    assert all(f.jti not in body["refresh_token"] for f in filas)


# --- Cambio de contraseña -------------------------------------------------------


def test_cambiar_la_contrasena_cierra_las_sesiones(client):
    """Si alguien te la había robado, cambiarla sin echarlo no le quita el acceso."""
    name = _name()
    body = register(client, name)
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "NuevaClave1234"},
        headers=headers,
    )
    assert resp.status_code == 204

    assert client.post(
        "/api/auth/refresh", json={"refresh_token": body["refresh_token"]}
    ).status_code == 401
    assert client.post(
        "/api/auth/login", json={"login": name, "password": PASSWORD}
    ).status_code == 401
    assert client.post(
        "/api/auth/login", json={"login": name, "password": "NuevaClave1234"}
    ).status_code == 200


def test_no_se_cambia_sin_saber_la_actual(client):
    headers = auth_headers(client)
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "NoEsLaSuya123", "new_password": "OtraClave12345"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_la_nueva_no_puede_ser_la_misma(client):
    headers = auth_headers(client)
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": PASSWORD, "new_password": PASSWORD},
        headers=headers,
    )
    assert resp.status_code == 400


def test_la_nueva_tambien_pasa_la_politica(client):
    headers = auth_headers(client)
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "floja"},
        headers=headers,
    )
    assert resp.status_code == 422


# --- Confirmación de email ------------------------------------------------------


def _last_code(user_id: str) -> str:
    with SessionLocal() as db:
        row = db.scalar(
            select(EmailVerification)
            .where(EmailVerification.user_id == user_id)
            .order_by(EmailVerification.created_at.desc())
        )
        return row.code


def test_el_codigo_no_viaja_en_la_respuesta(client):
    """Devolverlo convertiría la verificación en un trámite que cualquiera completa
    sin acceso al correo."""
    headers = auth_headers(client)
    resp = client.post("/api/auth/email", json={"email": f"{uuid.uuid4().hex[:8]}@example.com"})
    resp = client.post(
        "/api/auth/email", json={"email": f"{uuid.uuid4().hex[:8]}@example.com"}, headers=headers
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert set(cuerpo) == {"email", "sent_by_email"}
    assert cuerpo["sent_by_email"] is False  # sin SMTP en tests: va a la consola


def test_el_codigo_correcto_verifica_el_email(client):
    body = register(client)
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    email = f"{uuid.uuid4().hex[:8]}@example.com"

    client.post("/api/auth/email", json={"email": email}, headers=headers)
    assert client.get("/api/me", headers=headers).json()["emailVerified"] is False

    code = _last_code(body["user"]["id"])
    assert client.post(
        "/api/auth/email/verify", json={"code": code}, headers=headers
    ).status_code == 204

    me = client.get("/api/me", headers=headers).json()
    assert me["emailVerified"] is True
    assert me["email"] == email


def test_un_codigo_equivocado_no_verifica(client):
    body = register(client)
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    client.post(
        "/api/auth/email", json={"email": f"{uuid.uuid4().hex[:8]}@example.com"}, headers=headers
    )
    assert client.post(
        "/api/auth/email/verify", json={"code": "000000"}, headers=headers
    ).status_code == 400
    assert client.get("/api/me", headers=headers).json()["emailVerified"] is False


def test_los_intentos_estan_topados(client):
    """Seis dígitos se sacan a fuerza bruta en un rato si nadie cuenta los intentos."""
    body = register(client)
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    client.post(
        "/api/auth/email", json={"email": f"{uuid.uuid4().hex[:8]}@example.com"}, headers=headers
    )
    for _ in range(5):
        client.post("/api/auth/email/verify", json={"code": "000000"}, headers=headers)

    code = _last_code(body["user"]["id"])
    resp = client.post("/api/auth/email/verify", json={"code": code}, headers=headers)
    assert resp.status_code == 400
    assert "intentos" in resp.json()["detail"].lower()


def test_pedir_un_codigo_nuevo_invalida_el_anterior(client):
    body = register(client)
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    email = f"{uuid.uuid4().hex[:8]}@example.com"

    client.post("/api/auth/email", json={"email": email}, headers=headers)
    viejo = _last_code(body["user"]["id"])
    client.post("/api/auth/email", json={"email": email}, headers=headers)

    assert client.post(
        "/api/auth/email/verify", json={"code": viejo}, headers=headers
    ).status_code == 400


def test_no_se_puede_reclamar_el_email_de_otra_persona(client):
    email = f"{uuid.uuid4().hex[:8]}@example.com"
    register(client, email=email)

    otra = auth_headers(client)
    assert client.post("/api/auth/email", json={"email": email}, headers=otra).status_code == 409


def test_el_email_no_verificado_no_da_acceso_a_nada_extra(client):
    """La cuenta funciona igual sin verificar: el email solo sirve para recuperar."""
    body = register(client, email=f"{uuid.uuid4().hex[:8]}@example.com")
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    assert body["user"]["emailVerified"] is False
    assert client.get("/api/bedtime/tonight", headers=headers).status_code == 200


def test_el_hash_no_es_la_contrasena(client):
    body = register(client)
    with SessionLocal() as db:
        user = db.get(User, body["user"]["id"])
        assert PASSWORD not in user.password_hash
        assert user.password_hash.startswith("$argon2")


def test_los_tokens_llevan_el_tipo_en_las_claims(client):
    body = register(client)
    access = jwt.decode(body["access_token"], settings.JWT_SECRET, algorithms=["HS256"])
    refresh = jwt.decode(body["refresh_token"], settings.JWT_SECRET, algorithms=["HS256"])
    assert access["type"] == tokens.ACCESS
    assert refresh["type"] == tokens.REFRESH
    assert access["exp"] < refresh["exp"]
