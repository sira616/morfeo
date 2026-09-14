"""Cabeceras de seguridad en cada respuesta.

Ninguna de estas cabeceras arregla un fallo por sí sola: suben el suelo. Si algún día
se cuela un XSS, la CSP corta la mayoría de las vías de explotarlo; si alguien intenta
embeber la app en un iframe para engañar al usuario, `frame-ancestors` lo impide. Son
gratis y no dependen de acordarse de nada, que es justo lo que les da valor.

La CSP está atada a lo que la app carga de verdad, no copiada de una plantilla. Cada
origen permitido tiene un motivo escrito al lado, para que al añadir un recurso nuevo
se vea qué hay que tocar en vez de aflojarla entera a base de comodines.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Construida por partes para poder comentar cada permiso. Sin esto, una CSP es una
# línea ilegible que nadie se atreve a tocar y acaba con 'unsafe-inline' en todo.
_CSP = "; ".join(
    [
        # Por defecto, nada de fuera. Todo lo que se salga hay que declararlo abajo.
        "default-src 'self'",
        # El bundle de Vite es un <script type=module> servido desde el propio origen.
        # No hay scripts inline, así que aquí NO hace falta 'unsafe-inline': mantenerlo
        # fuera es lo que hace que la CSP sirva de algo contra un XSS.
        "script-src 'self'",
        # 'unsafe-inline' aquí y no en script-src: la app usa muchísimos style={{...}}
        # de React, que son atributos de estilo inline y sin esto se bloquean. El
        # riesgo de inyección por estilo es mucho menor que por script. La hoja de
        # Google Fonts se sirve desde fonts.googleapis.com.
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        # Los ficheros de fuente reales los sirve gstatic, no googleapis.
        "font-src 'self' https://fonts.gstatic.com",
        # El favicon es un SVG propio; data: deja los iconos y las imágenes embebidas.
        "img-src 'self' data:",
        # La API va en el mismo origen que la SPA (el backend sirve el build), así que
        # 'self' basta. Si algún día el frontend llama a otro host, se añade aquí.
        "connect-src 'self'",
        "manifest-src 'self'",
        # Equivale a X-Frame-Options: DENY, pero es el mecanismo moderno y más fino.
        "frame-ancestors 'none'",
        # Un <base> inyectado podría repuntar todas las URLs relativas a otro sitio.
        "base-uri 'self'",
        # No hay formularios que posteen fuera; cerrarlo corta una vía de exfiltración.
        "form-action 'self'",
        "object-src 'none'",
    ]
)

_HEADERS = {
    "Content-Security-Policy": _CSP,
    # El navegador no adivina el tipo de un recurso: si el servidor dice JSON, es JSON.
    # Cierra los ataques que hacen pasar un .txt subido por un script ejecutable.
    "X-Content-Type-Options": "nosniff",
    # Redundante con frame-ancestors para navegadores viejos que no leen CSP.
    "X-Frame-Options": "DENY",
    # No filtrar la URL completa (que puede llevar rutas internas) a sitios de fuera.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # La app no usa cámara, micrófono ni geolocalización: se apagan explícitamente para
    # que un script colado tampoco pueda pedirlos.
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        for nombre, valor in _HEADERS.items():
            # setdefault y no asignación directa: si una respuesta concreta ya fijó su
            # propia cabecera por un motivo, no se la pisamos.
            response.headers.setdefault(nombre, valor)
        return response
