from __future__ import annotations

from datetime import date as date_type
from datetime import datetime, time
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SleepNight(Base):
    """Una noche medida por el reloj.

    `night_of` es la fecha en que se fue a dormir, no la del despertar: así una noche
    del viernes al sábado se agrupa bajo el viernes, que es como la cuenta la gente.
    """

    __tablename__ = "sleep_nights"
    __table_args__ = (UniqueConstraint("user_id", "night_of", name="uq_sleep_night_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    night_of: Mapped[date_type] = mapped_column(index=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")

    bed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sleep_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sleep_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    out_of_bed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    total_sleep_minutes: Mapped[int] = mapped_column(Integer)
    time_in_bed_minutes: Mapped[int] = mapped_column(Integer)
    # Latencia real de conciliación: el dato que diferencia esta app de una
    # calculadora de "ocho horas antes de la alarma".
    onset_latency_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    awakenings: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    deep_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rem_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    light_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    resting_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hrv_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    @property
    def efficiency(self) -> float:
        if not self.time_in_bed_minutes:
            return 0.0
        return self.total_sleep_minutes / self.time_in_bed_minutes


class DailyMetrics(Base):
    """Lo que el reloj mide durante el día y alimenta el cálculo de esta noche."""

    __tablename__ = "daily_metrics"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_daily_metrics_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date_type] = mapped_column(index=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")

    steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exercise_minutes: Mapped[int] = mapped_column(Integer, default=0)
    exercise_intensity: Mapped[str] = mapped_column(String(16), default="none")
    exercise_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    # 0-100, más alto es más estrés. Cada adaptador normaliza a esta escala.
    stress_avg: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    resting_hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hrv_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Checkin(Base):
    """Lo que el reloj no puede saber, sacado de la conversación casual de la tarde.

    `transcript` guarda lo que la persona escribió y `extracted` el JSON que el LLM
    dedujo. Se guardan los dos a propósito: si mañana se cambia el prompt o el modelo,
    se pueden reextraer los campos sin haber perdido el original.
    """

    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_checkin_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date_type] = mapped_column(index=True)

    mood: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    energy: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    perceived_stress: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    nap_minutes: Mapped[int] = mapped_column(Integer, default=0)
    last_caffeine: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    alcohol: Mapped[bool] = mapped_column(Boolean, default=False)
    wake_target: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON crudo del LLM

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BedtimeRecommendation(Base):
    """Una recomendación emitida, congelada con los factores que la produjeron.

    `followed` y la noche que vino después son lo que permite evaluar el motor: sin
    guardar la recomendación no hay forma de saber si acertaba.
    """

    __tablename__ = "bedtime_recommendations"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_recommendation_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date_type] = mapped_column(index=True)

    wake_target: Mapped[time] = mapped_column(Time)
    bedtime: Mapped[time] = mapped_column(Time)
    window_start: Mapped[time] = mapped_column(Time)
    window_end: Mapped[time] = mapped_column(Time)

    target_sleep_minutes: Mapped[int] = mapped_column(Integer)
    time_in_bed_minutes: Mapped[int] = mapped_column(Integer)
    onset_latency_minutes: Mapped[int] = mapped_column(Integer)
    mode: Mapped[str] = mapped_column(String(16), default="normal")
    confidence: Mapped[str] = mapped_column(String(8), default="baja")

    factors: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    notes: Mapped[str] = mapped_column(Text, default="[]")  # JSON

    followed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
