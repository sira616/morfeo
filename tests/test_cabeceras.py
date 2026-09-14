"""Tests de las cabeceras de seguridad.

El frontend guarda el refresh token en `localStorage`, así que treinta días de sesión
están al alcance de cualquier script que llegue a ejecutarse en la página. Estas
cabeceras son lo que impide que llegue a ejecutarse, y por eso tienen test propio: es
el tipo de cosa que desaparece en un refactor sin que falle nada visible.
"""
import pytest

from app.core.headers import CSP


def _directiva(nombre: str) -> str:
    for trozo in CSP.split("; "):
        if trozo.split(" ")[0] == nombre:
            return trozo
    raise AssertionError(f"La CSP no tiene directiva '{nombre}': {CSP}")


def test_la_respuesta_lleva_csp_y_las_demas(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers["content-security-policy"] == CSP
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"


def test_tambien_en_las_respuestas_de_error(client):
    """Un 401 se pinta en el navegador igual que un 200. Dejar fuera los errores es la
    forma más fácil de tener una CSP que parece puesta y no cubre media aplicación."""
    resp = client.get("/api/me")
    assert resp.status_code == 401
    assert "content-security-policy" in resp.headers


@pytest.mark.parametrize("flojo", ["'unsafe-inline'", "'unsafe-eval'"])
def test_los_scripts_no_admiten_nada_inline(flojo):
    """Lo único que de verdad protege el token. El build de Vite mete todo el JS en
    ficheros con hash, así que no hay ninguna excusa para aflojar esto."""
    assert flojo not in _directiva("script-src")


def test_no_se_puede_mandar_nada_a_otro_sitio():
    """Aunque alguien consiguiera ejecutar algo, no tendría a dónde exfiltrarlo."""
    assert _directiva("connect-src") == "connect-src 'self'"


def test_la_pagina_no_se_deja_empotrar():
    assert _directiva("frame-ancestors") == "frame-ancestors 'none'"
