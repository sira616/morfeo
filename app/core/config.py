from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Entorno: "production" | "development". Por defecto production, que es el valor
    # seguro: un despliegue al que se le olvide definirlo no expone /docs.
    ENVIRONMENT: str = "production"

    # SQLite basta para una app personal de una sola persona. Postgres solo hace falta
    # si algún día hay concurrencia real.
    DATABASE_URL: str = "sqlite:///./morfeo.db"

    # Auth (Supabase Auth gestiona credenciales, tokens, verificación de email y MFA)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Solo desarrollo local: sustituye Supabase Auth por un doble en memoria
    # (app/core/dev_auth.py) para levantar el backend sin un proyecto de Supabase.
    LOCAL_DEV_AUTH: bool = False

    # LLM: "cloud" (Claude) o "local" (Ollama). Con datos de sueño y de ánimo, el modo
    # local no es un capricho: son datos de salud y hay quien no querrá mandarlos fuera.
    LLM_PROVIDER: str = "cloud"
    ANTHROPIC_API_KEY: str = ""
    LLM_CLOUD_MODEL: str = "claude-haiku-4-5-20251001"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    OLLAMA_API_KEY: str = ""

    # Wearable. `oura` usa un Personal Access Token del panel de Oura; el resto de
    # proveedores entran por /api/sleep/import o por la API manual.
    OURA_ACCESS_TOKEN: str = ""

    # Build del frontend a servir desde el propio backend. Vacío = solo API (que es
    # lo que se quiere en desarrollo, donde el frontend lo sirve Vite).
    FRONTEND_DIST: str = ""

    # Cuentas con acceso al panel de /dev. El rol nunca llega del cliente: se deriva
    # de esta lista, así que promocionar a alguien es editar el .env y reiniciar.
    ADMIN_EMAILS: list[str] = []

    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ]

    # Rate limiting (en memoria, ver app/core/rate_limit.py)
    RATE_LIMIT_MAX_REQUESTS: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# --- Fail-fast de configuración -------------------------------------------------
# Un backend que arranca "a medias" convierte un error de despliegue en un 500 opaco
# en la primera petición del usuario. Preferimos no arrancar y decir qué falta.

IS_PRODUCTION = settings.ENVIRONMENT.strip().lower() == "production"

# LOCAL_DEV_AUTH sustituye la autenticación real por un doble en memoria: cualquier
# email y contraseña crean cuenta. Combinarlo con producción deja el backend abierto.
if settings.LOCAL_DEV_AUTH and IS_PRODUCTION:
    raise RuntimeError(
        "LOCAL_DEV_AUTH=true no puede usarse con ENVIRONMENT=production: sustituye la "
        "autenticación por un doble en memoria y dejaría el backend sin auth real. "
        "Usa ENVIRONMENT=development en local, o quita LOCAL_DEV_AUTH en el despliegue."
    )

_REQUIRED_SUPABASE_SETTINGS = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY")
_missing = [name for name in _REQUIRED_SUPABASE_SETTINGS if not getattr(settings, name).strip()]

if _missing and not settings.LOCAL_DEV_AUTH:
    raise RuntimeError(
        "Faltan variables de entorno obligatorias de Supabase: "
        + ", ".join(_missing)
        + ". Sin ellas la autenticación no puede validar ni emitir tokens. "
        "Rellénalas en .env (desarrollo) o en las variables del servicio de despliegue."
    )

if (
    not settings.LOCAL_DEV_AUTH
    and settings.SUPABASE_ANON_KEY.strip() == settings.SUPABASE_SERVICE_ROLE_KEY.strip()
):
    raise RuntimeError(
        "SUPABASE_ANON_KEY y SUPABASE_SERVICE_ROLE_KEY son iguales. La service_role key "
        "salta las políticas RLS de Supabase: usarla donde va la anon key deja toda la "
        "base de datos accesible. Revisa Settings -> API en el dashboard de Supabase."
    )

# `allow_credentials=True` en app/main.py hace que el navegador rechace un origen `*`,
# pero además un comodín aquí anularía el control de qué frontend puede llamar a la API.
if "*" in settings.ALLOWED_ORIGINS:
    raise RuntimeError(
        "ALLOWED_ORIGINS no puede contener '*': la API se sirve con credenciales "
        "(cabecera Authorization) y necesita una lista explícita de orígenes."
    )
