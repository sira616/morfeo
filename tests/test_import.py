"""Tests del importador. Los mensajes de error se comprueban a propósito: quien
importa está mapeando columnas a mano y un 422 genérico no le dice qué arreglar."""
import json
from datetime import date

import pytest

from app.wearables.fileimport import MAX_ROWS, FileImportProvider, ImportError_, parse_nights

NOCHE = {"night_of": "2026-09-05", "total_sleep_minutes": 412, "time_in_bed_minutes": 470}


def test_json_minimo():
    nights = parse_nights(json.dumps([NOCHE]))
    assert len(nights) == 1
    assert nights[0].night_of == date(2026, 9, 5)
    assert nights[0].total_sleep_minutes == 412


def test_csv_con_las_mismas_columnas():
    csv = "night_of,total_sleep_minutes,time_in_bed_minutes\n2026-09-05,412,470\n"
    nights = parse_nights(csv, "csv")
    assert nights[0].time_in_bed_minutes == 470


def test_json_invalido_dice_que_no_es_json():
    with pytest.raises(ImportError_, match="no es JSON válido"):
        parse_nights("{esto no es json")


def test_columna_que_falta_se_nombra():
    incompleta = {"night_of": "2026-09-05", "total_sleep_minutes": 412}
    with pytest.raises(ImportError_, match="time_in_bed_minutes"):
        parse_nights(json.dumps([incompleta]))


def test_fecha_mal_formada_dice_la_fila():
    with pytest.raises(ImportError_, match="Fila 1"):
        parse_nights(json.dumps([{**NOCHE, "night_of": "05/09/2026"}]))


def test_dormir_mas_que_estar_en_la_cama_apunta_al_mapeo():
    """El error típico de mapear mal las columnas, y el más silencioso: sin esta
    comprobación entra en la base de datos una eficiencia mayor que 1."""
    roto = {**NOCHE, "total_sleep_minutes": 470, "time_in_bed_minutes": 412}
    with pytest.raises(ImportError_, match="mapeo de columnas"):
        parse_nights(json.dumps([roto]))


def test_tope_de_filas():
    demasiadas = json.dumps([NOCHE] * (MAX_ROWS + 1))
    with pytest.raises(ImportError_, match=str(MAX_ROWS)):
        parse_nights(demasiadas)


def test_campos_opcionales_ilegibles_no_rompen_la_importacion():
    """Un `resting_hr` vacío o con basura vale null: perder la noche entera por una
    columna secundaria sería peor que importarla incompleta."""
    nights = parse_nights(json.dumps([{**NOCHE, "resting_hr": "", "deep_minutes": "n/a"}]))
    assert nights[0].resting_hr is None
    assert nights[0].deep_minutes is None


def test_el_proveedor_filtra_por_rango():
    nights = parse_nights(
        json.dumps([NOCHE, {**NOCHE, "night_of": "2026-09-20"}])
    )
    provider = FileImportProvider(nights)
    dentro = provider.fetch_nights(date(2026, 9, 1), date(2026, 9, 10))
    assert [n.night_of for n in dentro] == [date(2026, 9, 5)]
