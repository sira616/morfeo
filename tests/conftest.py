import os
import tempfile
import uuid
from types import SimpleNamespace

import pytest

# Debe fijarse antes de importar app.core.config / app.core.database (SQLite en archivo temporal).
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["ANTHROPIC_API_KEY"] = ""
# app/core/config.py aborta el arranque si falta cualquiera de estas: los tests importan
# la app entera, así que necesitan valores (ficticios, el cliente real se sustituye por
# FakeSupabaseAuth más abajo).
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key-solo-para-tests")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key-solo-para-tests")
# El fixture "client" es scope=session y varios módulos comparten /register y /login:
# un límite bajo aquí haría que un test le robara cupo a otro. El rate limiting en sí
# se testea de forma aislada en test_security.py.
os.environ["RATE_LIMIT_MAX_REQUESTS"] = "10000"
os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "60"
# Forzar "cloud" (modo demo, instantáneo) pase lo que pase en el .env del desarrollador —
# si no, con LLM_PROVIDER=local los tests golpearían un Ollama real y serían lentos/no deterministas.
os.environ["LLM_PROVIDER"] = "cloud"

from fastapi.testclient import TestClient  # noqa: E402
from supabase_auth.errors import AuthApiError  # noqa: E402

from app.core.database import engine  # noqa: E402
import app.api.auth as auth_module  # noqa: E402
import app.core.security as security_module  # noqa: E402


class FakeSupabaseAuth:
    """Doble en memoria de `Client.auth` — evita llamadas de red reales a Supabase en los tests,
    igual que `retrieve`/`generate` se mockean para Qdrant/Anthropic."""

    def __init__(self):
        self.users_by_email: dict[str, dict] = {}
        self.access_tokens: dict[str, str] = {}
        self.refresh_tokens: dict[str, str] = {}
        self.sessions: dict[str, str] = {}  # access_token -> refresh_token (misma sesión)

    def sign_up(self, credentials):
        email, password = credentials["email"], credentials["password"]
        if email in self.users_by_email:
            raise AuthApiError("User already registered", 400, "email_exists")
        user_id = str(uuid.uuid4())
        self.users_by_email[email] = {"id": user_id, "password": password}
        return SimpleNamespace(user=SimpleNamespace(id=user_id, email=email), session=None)

    def sign_in_with_password(self, credentials):
        email, password = credentials["email"], credentials["password"]
        record = self.users_by_email.get(email)
        if record is None or record["password"] != password:
            raise AuthApiError("Invalid login credentials", 400, "invalid_credentials")

        user_id = record["id"]
        access_token, refresh_token = f"access-{uuid.uuid4()}", f"refresh-{uuid.uuid4()}"
        self.access_tokens[access_token] = user_id
        self.refresh_tokens[refresh_token] = user_id
        self.sessions[access_token] = refresh_token
        session = SimpleNamespace(access_token=access_token, refresh_token=refresh_token)
        return SimpleNamespace(user=SimpleNamespace(id=user_id, email=email), session=session)

    def refresh_session(self, refresh_token=None):
        user_id = self.refresh_tokens.pop(refresh_token, None)
        if user_id is None:
            raise AuthApiError("Invalid Refresh Token", 401, "refresh_token_not_found")

        new_access, new_refresh = f"access-{uuid.uuid4()}", f"refresh-{uuid.uuid4()}"
        self.access_tokens[new_access] = user_id
        self.refresh_tokens[new_refresh] = user_id
        self.sessions[new_access] = new_refresh
        session = SimpleNamespace(access_token=new_access, refresh_token=new_refresh)
        return SimpleNamespace(session=session, user=None)

    def get_user(self, jwt=None):
        user_id = self.access_tokens.get(jwt)
        if user_id is None:
            return None
        email = next(e for e, r in self.users_by_email.items() if r["id"] == user_id)
        return SimpleNamespace(user=SimpleNamespace(id=user_id, email=email))

    @property
    def admin(self):
        outer = self

        class _Admin:
            def sign_out(self, jwt, scope="global"):
                refresh_token = outer.sessions.pop(jwt, None)
                outer.access_tokens.pop(jwt, None)
                if refresh_token is not None:
                    outer.refresh_tokens.pop(refresh_token, None)

        return _Admin()


_fake_client = SimpleNamespace(auth=FakeSupabaseAuth())
auth_module.get_supabase = lambda: _fake_client
auth_module.get_supabase_admin = lambda: _fake_client
security_module.get_supabase = lambda: _fake_client

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
    engine.dispose()
    os.close(_db_fd)
    try:
        os.unlink(_db_path)
    except OSError:
        pass  # Windows a veces tarda en soltar el handle del fichero; no es un fallo real
