"""Importador de exportaciones de reloj (JSON o CSV).

El proveedor que hace que la app funcione con *cualquier* reloj desde el primer día.
Garmin, Fitbit, Samsung Health, Apple Salud y Withings dejan descargar el histórico;
esa descarga se mapea aquí sin depender de que ninguna API te apruebe la aplicación.

También es la forma de tener datos con los que trabajar antes de decidir integración,
y de rellenar huecos cuando una API falla.

Formato aceptado (JSON, una lista de objetos; el CSV usa las mismas columnas):

    [{"night_of": "2026-09-05", "total_sleep_minutes": 412,
      "time_in_bed_minutes": 470, "onset_latency_minutes": 35}]
"""
from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime

from app.wearables.base import NightSample

REQUIRED_COLUMNS = ("night_of", "total_sleep_minutes", "time_in_bed_minutes")

# Un histórico completo de un reloj son unos pocos miles de filas. El tope evita que
# un fichero mal formado (o malicioso) haga crecer la memoria sin control.
MAX_ROWS = 5000


class ImportError_(ValueError):
    """Error de formato del fichero, con un mensaje pensado para enseñárselo al usuario."""


def _to_int(value: object, field: str, row_number: int) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        raise ImportError_(f"Fila {row_number}: '{field}' no es un número ({value!r})") from None


def _optional_int(value: object) -> int | None:
    if value in (None, "", "null"):
        return None
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _to_datetime(value: object) -> datetime | None:
    if value in (None, "", "null"):
        return None
    try:
        return datetime.fromisoformat(str(value)).replace(tzinfo=None)
    except ValueError:
        return None


def parse_nights(raw: str, content_type: str = "json") -> list[NightSample]:
    """Convierte el contenido de un fichero en noches. No toca base de datos."""
    if content_type == "csv":
        rows = list(csv.DictReader(io.StringIO(raw)))
    else:
        try:
            rows = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ImportError_(f"El fichero no es JSON válido: {exc.msg}") from None
        if not isinstance(rows, list):
            raise ImportError_("Se esperaba una lista de noches en el nivel superior del JSON")

    if len(rows) > MAX_ROWS:
        raise ImportError_(f"El fichero trae {len(rows)} filas; el máximo son {MAX_ROWS}")

    nights: list[NightSample] = []
    for number, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ImportError_(f"Fila {number}: se esperaba un objeto, llegó {type(row).__name__}")
        missing = [c for c in REQUIRED_COLUMNS if row.get(c) in (None, "")]
        if missing:
            raise ImportError_(f"Fila {number}: faltan las columnas {', '.join(missing)}")

        try:
            night_of = date.fromisoformat(str(row["night_of"])[:10])
        except ValueError:
            raise ImportError_(
                f"Fila {number}: 'night_of' debe ser una fecha AAAA-MM-DD, llegó "
                f"{row['night_of']!r}"
            ) from None

        total = _to_int(row["total_sleep_minutes"], "total_sleep_minutes", number)
        in_bed = _to_int(row["time_in_bed_minutes"], "time_in_bed_minutes", number)
        if in_bed < total:
            raise ImportError_(
                f"Fila {number}: se duerme más ({total} min) de lo que se está en la cama "
                f"({in_bed} min). Revisa el mapeo de columnas."
            )

        nights.append(
            NightSample(
                night_of=night_of,
                total_sleep_minutes=total,
                time_in_bed_minutes=in_bed,
                bed_at=_to_datetime(row.get("bed_at")),
                sleep_start=_to_datetime(row.get("sleep_start")),
                sleep_end=_to_datetime(row.get("sleep_end")),
                onset_latency_minutes=_optional_int(row.get("onset_latency_minutes")),
                awakenings=_optional_int(row.get("awakenings")),
                deep_minutes=_optional_int(row.get("deep_minutes")),
                rem_minutes=_optional_int(row.get("rem_minutes")),
                light_minutes=_optional_int(row.get("light_minutes")),
                resting_hr=_optional_int(row.get("resting_hr")),
            )
        )
    return nights


class FileImportProvider:
    """Cumple el contrato de `WearableProvider` sobre datos ya cargados en memoria."""

    name = "import"

    def __init__(self, nights: list[NightSample]) -> None:
        self._nights = nights

    def fetch_nights(self, since: date, until: date) -> list[NightSample]:
        return [n for n in self._nights if since <= n.night_of <= until]

    def fetch_days(self, since: date, until: date) -> list:
        return []
