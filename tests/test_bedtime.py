"""Tests del motor. Sin base de datos, sin red y sin reloj del sistema: el motor es
puro, así que estos tests son deterministas por construcción."""
from datetime import time

import pytest

from app.domain.bedtime import (
    MAX_WAKE_IN_BED_MINUTES,
    RESTRICTION_FLOOR_MINUTES,
    SLEEP_NEED_CEILING_MINUTES,
    DaySignals,
    SleepProfile,
    build_profile,
    recommend_bedtime,
    sleep_debt,
)

WAKE = time(7, 0)


def test_caso_base_descuenta_la_latencia_de_conciliacion():
    """El punto entero de la app: la hora es de meterse en la cama, no de dormirse.

    8 h de objetivo con eficiencia 1.0 son 480 min en la cama, que desde las 07:00
    llevan a las 23:00. Los 20 min de conciliación adelantan la hora a las 22:40: es
    la diferencia entre "acuéstate a las 23:00" y dormir de verdad ocho horas.
    """
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(sleep_need_minutes=480, onset_latency_minutes=20, efficiency=1.0),
        DaySignals(),
    )
    assert rec.bedtime == time(22, 40)
    assert rec.onset_latency_minutes == 20
    assert rec.mode == "normal"


def test_la_eficiencia_alarga_el_tiempo_en_cama():
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(sleep_need_minutes=480, onset_latency_minutes=0, efficiency=0.90),
        DaySignals(),
    )
    assert rec.time_in_bed_minutes == 533  # 480 / 0.90
    assert rec.bedtime == time(22, 7)


def test_la_deuda_se_recupera_a_plazos_y_con_tope():
    """400 min de deuda no son 400 min extra esta noche: son 60, que es el tope."""
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(sleep_need_minutes=480, onset_latency_minutes=0, efficiency=1.0),
        DaySignals(sleep_debt_minutes=400),
    )
    assert rec.target_sleep_minutes == 540
    assert any(f.label == "Deuda de sueño" and f.minutes == 60 for f in rec.factors)


def test_la_siesta_descuenta_la_mitad():
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(sleep_need_minutes=480, onset_latency_minutes=0, efficiency=1.0),
        DaySignals(nap_minutes=40),
    )
    assert rec.target_sleep_minutes == 460


def test_el_objetivo_nunca_pasa_del_techo():
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(sleep_need_minutes=600, onset_latency_minutes=0, efficiency=1.0),
        DaySignals(sleep_debt_minutes=600, stress=95, exercise_minutes=90, exercise_intensity="hard"),
    )
    assert rec.target_sleep_minutes == SLEEP_NEED_CEILING_MINUTES


def test_eficiencia_baja_comprime_la_ventana_en_vez_de_alargarla():
    """El comportamiento contraintuitivo que justifica el modo restricción.

    Alguien que pasa 9 h en la cama y duerme 6 no necesita acostarse antes: necesita
    dejar de usar la cama para estar despierto.
    """
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(
            sleep_need_minutes=480,
            onset_latency_minutes=30,
            efficiency=0.70,
            observed_sleep_minutes=360,
            nights_observed=14,
        ),
        DaySignals(),
    )
    assert rec.mode == "restriccion"
    assert rec.time_in_bed_minutes == 390  # 360 dormidos + 30 de margen
    assert rec.bedtime == time(0, 0)
    assert any("eficiencia" in n.lower() for n in rec.notes)


def test_la_restriccion_no_baja_del_suelo_de_seguridad():
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(
            sleep_need_minutes=480,
            onset_latency_minutes=0,
            efficiency=0.60,
            observed_sleep_minutes=180,
            nights_observed=20,
        ),
        DaySignals(),
    )
    assert rec.time_in_bed_minutes == RESTRICTION_FLOOR_MINUTES


def test_la_restriccion_exige_noches_suficientes():
    """Con dos noches medidas no se comprime nada: podría ser un fin de semana raro."""
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(
            sleep_need_minutes=480,
            onset_latency_minutes=0,
            efficiency=0.70,
            observed_sleep_minutes=360,
            nights_observed=2,
        ),
        DaySignals(),
    )
    assert rec.mode == "normal"
    assert rec.confidence == "baja"


def test_ejercicio_tardio_suma_latencia_y_deja_nota():
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(sleep_need_minutes=480, onset_latency_minutes=20, efficiency=1.0),
        DaySignals(exercise_minutes=60, exercise_intensity="hard", exercise_end=time(21, 30)),
    )
    assert rec.onset_latency_minutes == 35
    assert any("entrenar" in n for n in rec.notes)


def test_cafeina_tardia_suma_latencia():
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(sleep_need_minutes=480, onset_latency_minutes=20, efficiency=1.0),
        DaySignals(last_caffeine=time(18, 0)),
    )
    assert rec.onset_latency_minutes == 30
    assert any("Cafeína" in n for n in rec.notes)


def test_cafeina_de_la_manana_no_penaliza():
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(sleep_need_minutes=480, onset_latency_minutes=20, efficiency=1.0),
        DaySignals(last_caffeine=time(8, 0)),
    )
    assert rec.onset_latency_minutes == 20
    assert rec.notes == []


def test_la_hora_cruza_medianoche_sin_romperse():
    rec = recommend_bedtime(
        time(5, 0),
        SleepProfile(sleep_need_minutes=480, onset_latency_minutes=20, efficiency=1.0),
        DaySignals(),
    )
    assert rec.bedtime == time(20, 40)

    rec_tarde = recommend_bedtime(
        time(11, 0),
        SleepProfile(sleep_need_minutes=360, onset_latency_minutes=0, efficiency=1.0),
        DaySignals(),
    )
    assert rec_tarde.bedtime == time(5, 0)


def test_la_ventana_rodea_la_hora_recomendada():
    rec = recommend_bedtime(WAKE, SleepProfile(efficiency=1.0), DaySignals())
    assert rec.window_start < rec.bedtime < rec.window_end


@pytest.mark.parametrize(
    "noches, esperado", [(0, "baja"), (4, "baja"), (5, "media"), (13, "media"), (14, "alta")]
)
def test_confianza_por_noches_observadas(noches, esperado):
    rec = recommend_bedtime(WAKE, SleepProfile(nights_observed=noches), DaySignals())
    assert rec.confidence == esperado


def test_los_factores_explican_el_objetivo():
    """Los factores no son decorado: tienen que sumar el objetivo, o la explicación
    que ve el usuario estaría mintiendo."""
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(sleep_need_minutes=480, efficiency=1.0),
        DaySignals(sleep_debt_minutes=120, stress=80, nap_minutes=30, mood=2),
    )
    assert sum(f.minutes for f in rec.factors) == rec.target_sleep_minutes


def test_deuda_solo_acumula_deficit():
    """Dormir de más no genera crédito: nueve horas el sábado no cubren el lunes."""
    assert sleep_debt([480, 480, 480], 480) == 0
    assert sleep_debt([400, 600, 480], 480) == 80
    assert sleep_debt([400] * 20, 480, window=14) == 80 * 14


def test_build_profile_sin_datos_cae_en_los_valores_por_defecto():
    profile = build_profile([], [], [], sleep_need_minutes=450)
    assert profile.nights_observed == 0
    assert profile.sleep_need_minutes == 450


def test_build_profile_calcula_eficiencia_y_latencia_mediana():
    """La eficiencia se mide sobre el tiempo ya dormido, no sobre el tiempo en cama.

    1260 min dormidos entre 1350 de ventana (1440 en cama menos las tres latencias).
    Usar los 1440 crudos daría 0.875 y contaría la latencia dos veces, porque el motor
    la vuelve a sumar al calcular la hora.
    """
    profile = build_profile(
        recent_sleep_minutes=[420, 400, 440],
        recent_time_in_bed_minutes=[480, 480, 480],
        recent_latency_minutes=[10, 30, 50],
    )
    assert profile.efficiency == pytest.approx(1260 / 1350, abs=0.001)
    assert profile.onset_latency_minutes == 30
    assert profile.observed_sleep_minutes == 420
    assert profile.nights_observed == 3


def test_build_profile_usa_la_latencia_mediana_en_las_noches_sin_medir():
    """Una noche sin latencia medida no puede quedarse con el tiempo en cama crudo:
    inflaría su ventana y bajaría la eficiencia sin motivo."""
    profile = build_profile(
        recent_sleep_minutes=[400, 400],
        recent_time_in_bed_minutes=[480, 480],
        recent_latency_minutes=[40, None],
    )
    assert profile.efficiency == pytest.approx(800 / 880, abs=0.001)
    assert profile.onset_latency_minutes == 40


def test_build_profile_sin_latencias_medidas_asume_veinte_minutos():
    profile = build_profile(
        recent_sleep_minutes=[400],
        recent_time_in_bed_minutes=[480],
        recent_latency_minutes=[None],
    )
    assert profile.onset_latency_minutes == 20
    assert profile.efficiency == pytest.approx(400 / 460, abs=0.001)


def test_la_ventana_no_crece_sin_tope_con_eficiencia_mediocre():
    """El agujero que destapó la primera prueba con datos reales.

    Con eficiencia 0.86 y un objetivo de 9 h 10, `objetivo / eficiencia` daba 10 h 40
    en la cama y mandaba a dormir a las 19:08. Sin histórico que anclar la ventana, el
    tope de vigilia la deja en el objetivo más una hora.
    """
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(sleep_need_minutes=550, onset_latency_minutes=30, efficiency=0.86),
        DaySignals(),
    )
    assert rec.time_in_bed_minutes == 550 + MAX_WAKE_IN_BED_MINUTES
    assert rec.bedtime == time(20, 20)


def test_con_historico_la_ventana_se_ancla_en_lo_que_se_duerme_de_verdad():
    """Aunque la eficiencia sea buena y no toque modo restricción.

    Quien lleva tres semanas durmiendo 6 h 15 no va a dormir 9 h esta noche por estar
    11 en la cama. La ventana se ancla en lo observado más una hora de margen.
    """
    rec = recommend_bedtime(
        WAKE,
        SleepProfile(
            sleep_need_minutes=480,
            onset_latency_minutes=30,
            efficiency=0.88,
            observed_sleep_minutes=375,
            nights_observed=21,
        ),
        DaySignals(sleep_debt_minutes=1400),
    )
    assert rec.mode == "normal"
    assert rec.time_in_bed_minutes == 375 + MAX_WAKE_IN_BED_MINUTES
    assert rec.bedtime == time(23, 15)
    assert any("no añade sueño" in n for n in rec.notes)
