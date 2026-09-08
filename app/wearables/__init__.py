"""Adaptadores de reloj. Ver `app/wearables/base.py` para el contrato.

Estado de cada proveedor:

- `import`  — listo. Lee la exportación de cualquier reloj (JSON o CSV).
- `manual`  — listo. La app recibe las noches por API, sin fuente externa.
- `oura`    — listo. Personal Access Token, sin OAuth ni aprobación previa.
- `fitbit`  — pendiente. OAuth2 con PKCE, cuenta de desarrollador gratuita.
- `garmin`  — no planificado. Su Health API exige aprobación como socio; hasta
  entonces, la vía realista es exportar de Garmin Connect y usar `import`.
"""
from app.wearables.base import DaySample, NightSample, WearableProvider

__all__ = ["NightSample", "DaySample", "WearableProvider"]
