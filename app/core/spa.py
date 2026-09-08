"""Servir el frontend construido desde el propio backend.

En desarrollo el frontend lo sirve Vite y esto no se usa. Para el uso real desde el
móvil sí importa: deja **una sola URL y un solo proceso** que arrancar, en vez de dos
puertos y un proxy. Y de paso desaparece el CORS, porque todo viene del mismo origen.

Si `FRONTEND_DIST` no apunta a un build, el backend arranca igual y solo expone la
API. Es lo correcto: quedarse sin arrancar porque falta un `npm run build` sería
convertir un detalle de despliegue en una caída.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# El index no se cachea: es quien apunta a los assets con hash, y si el navegador se
# queda con uno viejo la app sigue pidiendo ficheros que ya no existen.
INDEX_HEADERS = {"Cache-Control": "no-cache"}


def mount_spa(app: FastAPI, dist: Path) -> bool:
    index = dist / "index.html"
    if not index.is_file():
        return False

    # Los assets llevan hash en el nombre, así que se pueden cachear para siempre.
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        """Ficheros reales si existen; si no, el index.

        La app es una SPA con rutas de cliente: entrar directo en `/historial` o
        recargar ahí tiene que devolver el index para que el router haga su trabajo,
        no un 404.
        """
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="No encontrado")

        candidate = (dist / full_path).resolve()
        # Sin esta comprobación, `GET /../../.env` saldría del directorio del build.
        if dist.resolve() in candidate.parents and candidate.is_file():
            return FileResponse(candidate)

        return FileResponse(index, headers=INDEX_HEADERS)

    return True
