"""Cabeceras de seguridad en cada respuesta.

Aquí importan más de lo que parece para una app doméstica. El frontend guarda el
refresh token —treinta días de sesión— en `localStorage`, que es una decisión
razonable (ver el README del frontend) pero que deja el token al alcance de cualquier
script que llegue a ejecutarse en la página. La CSP es lo que hace que ese script no
llegue a ejecutarse.

Lo que de verdad protege es `script-src 'self'`: sin `unsafe-inline` ni `unsafe-eval`,
un `<script>` inyectado no corre aunque alguien consiga escribirlo en el DOM. Y
`connect-src 'self'` remata la jugada: aunque corriera, no tendría a dónde mandar lo
que robe.

`style-src` sí lleva `'unsafe-inline'`, y no por dejadez: la interfaz usa `style={{…}}`
de React por todas partes. Es un aflojamiento de verdad —permite exfiltrar por
selectores CSS— pero de un orden de magnitud menos grave que permitir scripts, y
quitarlo obligaría a reescribir treinta componentes.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Las fuentes vienen de Google Fonts (ver el index.html del frontend). Si algún día se
# sirven desde el propio build, estas dos excepciones se caen y la política mejora.
_FUENTES_CSS = "https://fonts.googleapis.com"
_FUENTES_FICHEROS = "https://fonts.gstatic.com"

CSP = "; ".join(
    [
        "default-src 'self'",
        # Sin 'unsafe-inline' ni 'unsafe-eval'. El build de Vite mete todo el JS en
        # ficheros con hash bajo /assets, así que no hace falta ninguno de los dos.
        "script-src 'self'",
        f"style-src 'self' 'unsafe-inline' {_FUENTES_CSS}",
        f"font-src 'self' {_FUENTES_FICHEROS}",
        # blob: lo necesita el icono generado del manifest en algunos navegadores.
        "img-src 'self' data: blob:",
        # El check-in por SSE va al mismo origen, así que no hay que abrir nada más.
        "connect-src 'self'",
        "manifest-src 'self'",
        "worker-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "object-src 'none'",
    ]
)

OTRAS = {
    # Sin esto, un fichero subido que el navegador decida que es HTML se ejecuta como
    # HTML aunque lo sirvamos como texto.
    "X-Content-Type-Options": "nosniff",
    # `frame-ancestors` ya lo cubre en navegadores modernos; esto es para los que no.
    "X-Frame-Options": "DENY",
    # La URL de esta app no tiene por qué aparecer en los logs de nadie más.
    "Referrer-Policy": "no-referrer",
    # No hace falta ninguna de estas API, y pedirlas es siempre señal de que algo va mal.
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
}

# Swagger carga su JavaScript de un CDN, así que la CSP lo rompería. Solo existen
# fuera de producción (ver app/main.py), y el resto de cabeceras sí se les ponen.
_SIN_CSP = frozenset({"/docs", "/redoc", "/openapi.json"})


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for nombre, valor in OTRAS.items():
            response.headers.setdefault(nombre, valor)
        if request.url.path not in _SIN_CSP:
            response.headers.setdefault("Content-Security-Policy", CSP)
        return response
