"""Validación de la foto de perfil.

La foto llega como *data URL* en JSON, no como multipart: el navegador ya la
redimensiona a un cuadrado pequeño con un canvas antes de mandarla (ver el frontend),
así que aquí solo entra algo del orden de decenas de KB y no una foto de 8 MB del
carrete. Eso evita añadir `python-multipart` y `Pillow` al backend.

Que el navegador la re-codifique tiene un efecto de seguridad de propina: la imagen que
se guarda son píxeles recomprimidos, no el fichero original, así que cualquier carga
escondida en los metadatos del original no llega a la base. Pero un cliente malicioso
puede saltarse el canvas y mandar bytes a mano, así que aquí NO nos fiamos:

- Solo raster real: PNG, JPEG o WebP, comprobado por los *magic bytes*, no por lo que
  diga el cliente. **SVG queda fuera** a propósito: un SVG puede llevar `<script>`, y es
  el único formato de "imagen" que se ejecuta al pintarlo.
- El mime que se guarda lo decide esto a partir de los magic bytes, no el `data:` del
  cliente, para que no pueda colar `image/svg+xml` ni `text/html` disfrazados.
- Tope de tamaño: una foto de perfil no necesita más, y sin tope un POST llena la base.
"""
from __future__ import annotations

import base64
import binascii
import re

# 200 KB ya descodificado. El navegador manda ~15-30 KB (256 px); este margen deja
# sitio a un cliente honesto que use otra calidad, y corta a uno que mande un archivo.
MAX_AVATAR_BYTES = 200_000

# Límite del texto del data URL en el esquema: base64 abulta ~4/3, más el prefijo.
MAX_AVATAR_DATA_URL_CHARS = 300_000

_DATA_URL = re.compile(r"^data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)$")


class AvatarError(ValueError):
    """La foto no es válida. El mensaje es apto para enseñar al usuario."""


def _sniff_mime(raw: bytes) -> str | None:
    """El tipo real a partir de los primeros bytes. None si no es un raster conocido."""
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if raw[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return None


def normalize_avatar(data_url: str) -> str:
    """Valida el data URL y devuelve uno normalizado (mime tomado de los magic bytes).

    Lanza `AvatarError` con un mensaje presentable si algo no cuadra.
    """
    if len(data_url) > MAX_AVATAR_DATA_URL_CHARS:
        raise AvatarError("La imagen es demasiado grande.")

    match = _DATA_URL.match(data_url.strip())
    if match is None:
        raise AvatarError("Formato de imagen no admitido. Sube un PNG, JPEG o WebP.")

    try:
        raw = base64.b64decode(match.group(2), validate=True)
    except (binascii.Error, ValueError):
        raise AvatarError("La imagen está corrupta.")

    if len(raw) > MAX_AVATAR_BYTES:
        raise AvatarError("La imagen es demasiado grande.")
    if not raw:
        raise AvatarError("La imagen está vacía.")

    mime = _sniff_mime(raw)
    if mime is None:
        # El cliente dijo que era una imagen, pero los bytes no lo son. No nos fiamos
        # del `data:`; mandamos fuera lo que no es un raster de verdad (incluido SVG).
        raise AvatarError("El archivo no es una imagen válida.")

    # Se reconstruye con el mime real y el base64 canónico, por si el cliente mintió en
    # el prefijo o metió relleno raro.
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"
