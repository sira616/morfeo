"""Tests de las métricas del histórico. Puras: sin base de datos ni reloj."""
from datetime import date, datetime

import pytest

from app.domain.insights import (
    MIN_NIGHTS_FOR_REGULARITY,
    adherence_rate,
    circular_distance,
    current_streak,
    midpoint_minutes,
    regularity,
    social_jetlag,
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


def test_distancia_circular_toma_el_camino_corto():
    assert circular_distance(10, 1430) == 20
    assert circular_distance(0, 720) == 720


def test_jet_lag_social_compara_diario_con_fin_de_semana():
    """Viernes y sábado cuentan como fin de semana: es cuando se trasnocha."""
    dias = []
    for d in range(1, 15):
        day = date(2026, 9, d)
        # Punto medio a las 03:00 entre semana, a las 05:00 viernes y sábado.
        dias.append((day, 300 if day.weekday() in (4, 5) else 180))

    jetlag = social_jetlag(dias)
    assert jetlag is not None
    assert jetlag.minutes == 120
    assert jetlag.weekday_midpoint_minutes == pytest.approx(180, abs=1)


def test_sin_fines_de_semana_no_hay_jet_lag_que_calcular():
    dias = [(date(2026, 9, d), 180) for d in (1, 2, 3, 7, 8)]  # sin viernes ni sábado
    assert social_jetlag(dias) is None


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
