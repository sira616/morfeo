"""Las cabeceras de seguridad salen en cada respuesta y dicen lo que deben.

Un test de cabeceras no comprueba que la app sea segura: comprueba que estas concretas
no desaparezcan en un refactor. Es fácil quitar un middleware sin darse cuenta, y sin
esto no se notaría hasta la siguiente auditoría.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


ESPERADAS = {
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
}


def test_estan_en_una_respuesta_de_api(client):
    presentes = {k.lower() for k in client.get("/health").headers}
    faltan = {c for c in ESPERADAS if c.lower() not in presentes}
    assert not faltan, f"faltan cabeceras en /health: {faltan}"


def test_el_nosniff_y_el_frame_valen_lo_correcto(client):
    h = client.get("/health").headers
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"


def test_la_csp_permite_lo_que_la_app_carga_de_verdad(client):
    csp = client.get("/health").headers["Content-Security-Policy"]
    # Las fuentes de Google: el CSS por googleapis, los ficheros por gstatic.
    assert "https://fonts.googleapis.com" in csp
    assert "https://fonts.gstatic.com" in csp
    # Los style={{...}} de React necesitan 'unsafe-inline' en style-src.
    assert "'unsafe-inline'" in csp


def test_la_csp_no_afloja_los_scripts(client):
    """El punto de tener CSP: un XSS no puede ejecutar un <script> inyectado.

    Si algún día alguien mete 'unsafe-inline' o un comodín en script-src, la CSP deja
    de proteger justo de lo que protege, y hay que enterarse aquí y no en producción.
    """
    csp = client.get("/health").headers["Content-Security-Policy"]
    directivas = dict(
        (parte.split(" ", 1) + [""])[:2]
        for parte in (p.strip() for p in csp.split(";"))
        if parte
    )
    script_src = directivas.get("script-src", directivas.get("default-src", ""))
    assert "'unsafe-inline'" not in script_src, script_src
    assert "*" not in script_src, script_src


def test_object_y_frame_ancestors_cerrados(client):
    csp = client.get("/health").headers["Content-Security-Policy"]
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
