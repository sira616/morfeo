from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, bedtime, checkin, dev, insights, me, sleep
from app.core.config import IS_PRODUCTION, settings
from app.core.database import Base, engine
from app.models import (  # noqa: F401 — registran los modelos en Base.metadata
    AuditEvent,
    BedtimeRecommendation,
    Checkin,
    DailyMetrics,
    SleepNight,
    User,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.LOCAL_DEV_AUTH:
        print(
            "\n" + "!" * 78 + "\n"
            "!!  LOCAL_DEV_AUTH=true — Supabase Auth sustituido por un doble EN MEMORIA.\n"
            "!!  Los usuarios se pierden al reiniciar y los tokens no son JWT reales.\n"
            "!!  Solo para desarrollo local: NUNCA en un despliegue.\n" + "!" * 78 + "\n"
        )
    Base.metadata.create_all(bind=engine)
    yield


# En producción no se publican /docs, /redoc ni /openapi.json: son el mapa completo de
# la superficie de la API y ahorran a un atacante el trabajo de descubrimiento.
_docs_enabled = not IS_PRODUCTION

app = FastAPI(
    title="Morfeo — Backend",
    description="Recomendador de hora de acostarse a partir de datos de wearable.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    # Enumerados en vez de "*": la API se sirve con credenciales (cabecera
    # Authorization). Al añadir un endpoint con otro verbo hay que añadirlo aquí
    # también, o el preflight del navegador fallará.
    allow_methods=["GET", "POST", "PATCH", "PUT"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(sleep.router)
app.include_router(checkin.router)
app.include_router(bedtime.router)
app.include_router(insights.router)
app.include_router(dev.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
