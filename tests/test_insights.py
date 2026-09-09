"""Tests de las métricas del histórico. Puras: sin base de datos ni reloj."""
from datetime import date, datetime

import pytest

from app.domain.insights import (
    MIN_MEANINGFUL_DELTA_MINUTES,
    MIN_NIGHTS_FOR_REGULARITY,
    WeekStats,
    adherence_rate,
    associations,
    circular_delta,
    current_streak,
    midpoint_minutes,
    regularity,
    week_stats,
    weekly_highlights,
    within_window,
    worst_night_factors,
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


# --- Informe semanal --------------------------------------------------------------


def test_el_movimiento_de_la_hora_va_por_el_camino_corto():
    """De las 23:50 a las 00:20 hay media hora hacia delante, no veintitrés y media
    hacia atrás. Es el mismo motivo por el que la regularidad es circular."""
    assert circular_delta(20, 1430) == 30
    assert circular_delta(1430, 20) == -30
    assert circular_delta(180, 120) == 60


def test_la_ventana_que_cruza_medianoche_sigue_siendo_una_ventana():
    # De 23:40 a 00:20.
    assert within_window(1435, 1420, 20) is True
    assert within_window(10, 1420, 20) is True
    assert within_window(120, 1420, 20) is False
    # Y una que no cruza se comporta como un intervalo normal.
    assert within_window(1380, 1370, 1410) is True
    assert within_window(1360, 1370, 1410) is False


def test_una_semana_sin_horas_medidas_tiene_media_de_sueño_pero_no_de_fase():
    """Muchos importadores traen cuánto se durmió y no cuándo. Esas noches cuentan
    para la media, y la fase se queda en `None` en vez de en cero."""
    stats = week_stats([420, 400, 440], [0.9, 0.85, 0.95], [])
    assert stats.nights == 3
    assert stats.mean_sleep_minutes == 420
    assert stats.mean_midpoint_minutes is None
    assert stats.sd_midpoint_minutes is None


def _noche(factores: set[str], sueño: int) -> tuple[set[str], int]:
    return factores, sueño


def test_sale_lo_que_estuvo_en_las_peores_noches_y_no_en_las_demas():
    muestras = [
        _noche({"cafe_tarde"}, 300),
        _noche({"cafe_tarde"}, 310),
        _noche(set(), 320),
        _noche(set(), 450),
        _noche(set(), 460),
        _noche(set(), 470),
        _noche(set(), 480),
    ]
    factores = worst_night_factors(muestras)
    assert [f.key for f in factores] == ["cafe_tarde"]
    assert (factores[0].nights_worst, factores[0].of_worst) == (2, 3)
    assert (factores[0].nights_rest, factores[0].of_rest) == (0, 4)


def test_lo_que_pasa_todas_las_noches_no_explica_las_peores():
    muestras = [_noche({"cafe_tarde"}, 300 + i * 30) for i in range(7)]
    assert worst_night_factors(muestras) == []


def test_una_anecdota_en_una_sola_noche_no_sale():
    muestras = [_noche({"alcohol"}, 300)] + [_noche(set(), 400 + i) for i in range(6)]
    assert worst_night_factors(muestras) == []


def test_con_media_semana_no_se_buscan_culpables():
    muestras = [_noche({"alcohol"}, 300), _noche({"alcohol"}, 310), _noche(set(), 450)]
    assert worst_night_factors(muestras) == []


def _stats(sueño: int | None = 420, sd: int | None = 40, nights: int = 7) -> WeekStats:
    return WeekStats(
        nights=nights,
        mean_sleep_minutes=sueño,
        mean_efficiency=0.9,
        mean_midpoint_minutes=200,
        sd_midpoint_minutes=sd,
    )


def test_con_dos_noches_el_informe_lo_dice_en_vez_de_promediar():
    lineas = weekly_highlights(
        _stats(nights=2), _stats(), None, [], 0, 0, None
    )
    assert len(lineas) == 1
    assert "2 noches medidas" in lineas[0]


def test_un_cambio_pequeño_se_cuenta_como_que_no_hubo_cambio():
    """Diez minutos de diferencia entre dos semanas son ruido, y darles titular sería
    ruido con formato."""
    lineas = weekly_highlights(_stats(430), _stats(420), None, [], 0, 0, None)
    assert lineas[0] == "Dormiste prácticamente lo mismo que la semana anterior."


def test_el_informe_dice_hacia_donde_se_movio_la_hora_y_cuanto_se_durmio():
    lineas = weekly_highlights(_stats(460), _stats(420), 45, [], 3, 5, -90)
    texto = " ".join(lineas)
    assert "40 min más por noche" in texto
    assert "retrasó 45 min" in texto
    assert "3 de 5 noches" in texto
    assert "bajó 1 h 30 min" in texto
