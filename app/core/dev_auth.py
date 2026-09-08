"""Doble en memoria de Supabase Auth para desarrollo local.

Existe para poder levantar el backend sin un proyecto de Supabase: implementa la
misma superficie de `Client.auth` que usan `app/api/auth.py` y `app/core/security.py`
(`sign_up`, `sign_in_with_password`, `refresh_session`, `get_user`, `admin.sign_out`).

Es el mismo enfoque que `FakeSupabaseAuth` en `tests/conftest.py`, extraído aquí para
que también sirva al servidor de desarrollo y no solo a los tests.

NO ES PARA PRODUCCIÓN:
  - Los usuarios viven en memoria: al reiniciar el servidor hay que volver a registrarse.
  - Los tokens son cadenas aleatorias, no JWT firmados: no valen fuera de este proceso.
  - Las contraseñas se guardan en claro en memoria (nunca se escriben a disco).

Se activa solo con `LOCAL_DEV_AUTH=true` en el `.env`, que por defecto es `false`
(ver `app/core/config.py`).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from supabase_auth.errors import AuthApiError


class InMemorySupabaseAuth:
    def __init__(self) -> None:
        self.users_by_email: dict[str, dict] = {}
        self.access_tokens: dict[str, str] = {}
        self.refresh_tokens: dict[str, str] = {}
        self.sessions: dict[str, str] = {}  # access_token -> refresh_token (misma sesión)

    # --- operaciones en nombre del usuario (equivalente a la anon key) ---

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

        session = self._issue(record["id"])
        return SimpleNamespace(user=SimpleNamespace(id=record["id"], email=email), session=session)

    def refresh_session(self, refresh_token=None):
        user_id = self.refresh_tokens.pop(refresh_token, None)
        if user_id is None:
            raise AuthApiError("Invalid Refresh Token", 401, "refresh_token_not_found")
        return SimpleNamespace(session=self._issue(user_id), user=None)

    def get_user(self, jwt=None):
        user_id = self.access_tokens.get(jwt)
        if user_id is None:
            return None
        email = next(e for e, r in self.users_by_email.items() if r["id"] == user_id)
        return SimpleNamespace(user=SimpleNamespace(id=user_id, email=email))

    # --- operaciones de administración (equivalente a la service_role key) ---

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

    # --- interno ---

    def _issue(self, user_id: str) -> SimpleNamespace:
        access_token, refresh_token = f"access-{uuid.uuid4()}", f"refresh-{uuid.uuid4()}"
        self.access_tokens[access_token] = user_id
        self.refresh_tokens[refresh_token] = user_id
        self.sessions[access_token] = refresh_token
        return SimpleNamespace(access_token=access_token, refresh_token=refresh_token)


_client: SimpleNamespace | None = None


def get_dev_client() -> SimpleNamespace:
    """Cliente único del proceso; imita la forma `client.auth` de supabase-py."""
    global _client
    if _client is None:
        _client = SimpleNamespace(auth=InMemorySupabaseAuth())
    return _client
