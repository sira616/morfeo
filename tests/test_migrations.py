"""Tests de las migraciones.

El primero es el que de verdad importa: comprueba que aplicar las migraciones sobre una
base vacía deja **exactamente** el esquema que describen los modelos. Es el guardián
contra el fallo que ha mordido tres veces —cambiar un modelo y olvidar la migración—,
que no se notaba hasta que una ruta devolvía 500 en caliente con todo el código
correcto.
"""
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

import app.models  # noqa: F401 — registra los modelos en Base.metadata
from app.core.config import settings
from app.core.database import Base
from app.core.migrations import alembic_config, upgrade_to_head


@pytest.fixture
def base_migrada(tmp_path: Path, monkeypatch):
    """Una base vacía con todas las migraciones aplicadas."""
    url = f"sqlite:///{(tmp_path / 'migrada.db').as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    upgrade_to_head()
    engine = create_engine(url)
    yield engine
    engine.dispose()


def test_las_migraciones_dejan_el_esquema_de_los_modelos(base_migrada):
    with base_migrada.connect() as conn:
        diferencias = compare_metadata(MigrationContext.configure(conn), Base.metadata)

    assert diferencias == [], (
        "El esquema migrado no coincide con los modelos. Alguien cambió un modelo sin "
        "añadir la migración. Se arregla con:\n"
        '  venv\\Scripts\\python.exe -m alembic revision --autogenerate -m "qué cambia"\n'
        f"Diferencias: {diferencias}"
    )


def test_estan_todas_las_tablas(base_migrada):
    tablas = set(inspect(base_migrada).get_table_names())
    assert set(Base.metadata.tables) <= tablas
    # La tabla de control de Alembic: si falta, la base no sabe por dónde va.
    assert "alembic_version" in tablas


def test_hay_una_sola_cabeza():
    """Dos cabezas significan migraciones en paralelo sin fusionar, y entonces
    `upgrade head` falla sin decir gran cosa."""
    heads = ScriptDirectory.from_config(alembic_config()).get_heads()
    assert len(heads) == 1, f"Hay {len(heads)} cabezas: {heads}"


def test_todas_las_revisiones_bajan_y_suben(tmp_path: Path, monkeypatch):
    """Un `downgrade` roto no se nota hasta que hace falta deshacer algo con prisa."""
    url = f"sqlite:///{(tmp_path / 'ida-y-vuelta.db').as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", url)

    from alembic import command

    config = alembic_config()
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(url)
    try:
        assert set(Base.metadata.tables) <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
