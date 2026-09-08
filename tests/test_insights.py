"""Tests de las métricas del histórico. Puras: sin base de datos ni reloj."""
from datetime import date, datetime

import pytest

from app.domain.insights import (
    MIN_MEANINGFUL_DELTA_MINUTES,
    MIN_NIGHTS_FOR_REGULARITY,
    adherence_rate,
    associations,
    current_streak,
    midpoint_minutes,
    regularity,
)


def _midpoint(start: str, end: str) -> int:
    return midpoint_minutes(datetime.fromisoformat(start), datetime.fromisoformat(end))


def test_punto_medio_de_una_noche_normal():
    # De 23:00 a 07:00, el punto medio son las 03:00.
    assert _midpoint("2026-09-01T23:00", "2026-09-02T07:00") == 180


def test_la_regularidad_no_se_rompe_al_cruzar_medianoche():
    """El motivo de usar estadística circular.

    Puntos medios a las 23:50 y a las 00:10 distan veinte minutos, no veintitrés horas
    y cuarenta minutos. Con una media aritmética esta persona saldría irregularísima.
    """
    midpoints = [1430, 10, 1435, 5, 1440 - 5]
    reg = regularity(midpoints)
    assert reg is not None
    assert reg.sd_minutes < 30
    assert reg.score > 70


def test_horario_desordenado_puntua_bajo():
    reg = regularity([120, 400, 60, 300, 500, 90])
    assert reg is not None
    assert reg.score < 40


def test_horario_clavado_puntua_cien():
    reg = regularity([180] * 10)
    assert reg is not None
    assert reg.sd_minutes == 0
    assert reg.score == 100


def test_sin_noches_suficientes_no_se_inventa_una_puntuacion():
    assert regularity([180] * (MIN_NIGHTS_FOR_REGULARITY - 1)) is None


def test_la_racha_cuenta_desde_la_noche_mas_reciente():
    dias = [
        (date(2026, 9, 1), True),
        (date(2026, 9, 2), False),
        (date(2026, 9, 3), True),
        (date(2026, 9, 4), True),
    ]
    assert current_streak(dias) == 2


def test_un_dia_sin_responder_no_rompe_la_racha():
    """Castigar el olvido de marcarlo convertiría la racha en una obligación de
    registrar, que es el tipo de presión que estropea el sueño."""
    dias = [
        (date(2026, 9, 1), True),
        (date(2026, 9, 2), None),
        (date(2026, 9, 3), True),
    ]
    assert current_streak(dias) == 2


def test_la_adherencia_ignora_los_dias_sin_responder():
    dias = [
        (date(2026, 9, 1), True),
        (date(2026, 9, 2), None),
        (date(2026, 9, 3), False),
    ]
    assert adherence_rate(dias) == 0.5
    assert adherence_rate([(date(2026, 9, 1), None)]) is None


def _sample(factors: set[str], sleep: int, efficiency: float = 0.9):
    return (factors, sleep, efficiency)


def test_las_asociaciones_comparan_noches_con_y_sin_el_factor():
    muestras = [_sample({"alcohol"}, 340) for _ in range(4)]
    muestras += [_sample(set(), 430) for _ in range(6)]

    resultado = associations(muestras)
    assert [a.key for a in resultado] == ["alcohol"]
    alcohol = resultado[0]
    assert alcohol.nights_with == 4
    assert alcohol.nights_without == 6
    assert alcohol.delta_sleep_minutes == -90


def test_un_factor_con_pocas_noches_no_se_enseña():
    """Con dos noches cualquier diferencia es ruido, y enseñarla invita a concluir."""
    muestras = [_sample({"cannabis"}, 300) for _ in range(2)]
    muestras += [_sample(set(), 460) for _ in range(8)]
    assert associations(muestras) == []


def test_una_diferencia_pequeña_tampoco_se_enseña():
    """Diez minutos entran en la variación normal entre noches."""
    muestras = [_sample({"siesta"}, 425) for _ in range(5)]
    muestras += [_sample(set(), 435) for _ in range(5)]
    assert associations(muestras) == []

    grandes = [_sample({"siesta"}, 420) for _ in range(5)]
    grandes += [_sample(set(), 420 + MIN_MEANINGFUL_DELTA_MINUTES + 5) for _ in range(5)]
    assert [a.key for a in associations(grandes)] == ["siesta"]


def test_lo_que_mas_mueve_la_aguja_sale_primero():
    muestras = []
    for _ in range(5):
        muestras.append(_sample({"cafe_tarde", "alcohol"}, 320))
        muestras.append(_sample({"cafe_tarde"}, 400))
        muestras.append(_sample(set(), 440))

    resultado = associations(muestras)
    deltas = [abs(a.delta_sleep_minutes) for a in resultado]
    assert deltas == sorted(deltas, reverse=True)


def test_sin_muestras_no_hay_asociaciones():
    assert associations([]) == []
