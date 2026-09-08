from supabase import Client, create_client

from app.core.config import settings

_client: Client | None = None
_admin_client: Client | None = None


def get_supabase() -> Client:
    """Cliente con la anon key: sign_up/sign_in/refresh/get_user (operaciones en nombre del usuario)."""
    if settings.LOCAL_DEV_AUTH:
        from app.core.dev_auth import get_dev_client

        return get_dev_client()

    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _client


def get_supabase_admin() -> Client:
    """Cliente con la service_role key: operaciones de administración (p. ej. revocar sesión en logout)."""
    if settings.LOCAL_DEV_AUTH:
        # Mismo doble: en local no hay separación anon/service_role que emular.
        from app.core.dev_auth import get_dev_client

        return get_dev_client()

    global _admin_client
    if _admin_client is None:
        _admin_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _admin_client
