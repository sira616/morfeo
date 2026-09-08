import os
import tempfile
import uuid

import pytest

# Debe fijarse antes de importar app.core.config / app.core.database.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["ANTHROPIC_API_KEY"] = ""
# La autenticación es local, así que los tests no necesitan doblar ningún proveedor
# externo: firman y validan sus propios tokens con este secreto.
os.environ["JWT_SECRET"] = "secreto-solo-para-tests-con-longitud-de-sobra"
os.environ["ADMIN_USERNAMES"] = "[]"
os.environ["SMTP_HOST"] = ""
# El fixture "client" es scope=session y varios módulos comparten /register y /login:
# un límite bajo aquí haría que un test le robara cupo a otro. El rate limiting en sí
# se prueba de forma aislada.
os.environ["RATE_LIMIT_MAX_REQUESTS"] = "10000"
os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "60"
# Forzar "cloud" (modo demo, instantáneo) pase lo que pase en el .env del desarrollador:
# con LLM_PROVIDER=local los tests golpearían un Ollama real.
os.environ["LLM_PROVIDER"] = "cloud"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import engine  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "ContrasenaLarga123"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
    engine.dispose()
    os.close(_db_fd)
    try:
        os.unlink(_db_path)
    except OSError:
        pass  # Windows a veces tarda en soltar el handle; no es un fallo real


def register(client: TestClient, username: str | None = None, **extra) -> dict:
    """Crea una cuenta y devuelve la respuesta con tokens y perfil."""
    username = username or f"u{uuid.uuid4().hex[:12]}"
    resp = client.post(
        "/api/auth/register",
        json={"username": username, "password": PASSWORD, **extra},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def auth_headers(client: TestClient, username: str | None = None, **extra) -> dict:
    return {"Authorization": f"Bearer {register(client, username, **extra)['access_token']}"}
