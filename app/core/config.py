from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Entorno: "production" | "development". Por defecto production, que es el valor
    # seguro: un despliegue al que se le olvide definirlo no expone /docs.
    ENVIRONMENT: str = "production"

    # SQLite basta para una app personal de una sola persona. Postgres solo hace falta
    # si algún día hay concurrencia real.
    DATABASE_URL: str = "sqlite:///./morfeo.db"

    # --- Autenticación local ---
    # Secreto de firma de los JWT. Sin él no se arranca: generarlo al vuelo dejaría a
    # todo el mundo fuera en cada reinicio, que es justo lo que este despliegue evita.
    # Generar uno:  python -c "import secrets; print(secrets.token_urlsafe(48))"
    JWT_SECRET: str = ""
    ACCESS_TOKEN_MINUTES: int = 30
    REFRESH_TOKEN_MINUTES: int = 60 * 24 * 30

    # Cuentas con acceso al panel de /dev, por nombre de usuario.
    ADMIN_USERNAMES: list[str] = []

    # SMTP para los códigos de confirmación. Sin configurar, el código se escribe en la
    # consola del servidor: en una app doméstica es preferible a no poder verificar.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "morfeo@localhost"

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

    # Nombre con el que anunciarse por mDNS, para poder entrar desde el móvil como
    # http://morfeo.local:8000 sin depender de la IP. Vacío = no se anuncia nada, que
    # es lo que se quiere en desarrollo y en los tests: un responder por sesión de
    # pytest sería ruido en la red de quien lo ejecute. Lo pone scripts\morfeo.ps1.
    MDNS_NAME: str = ""
    MDNS_PORT: int = 8000

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

if not settings.JWT_SECRET.strip():
    raise RuntimeError(
        "Falta JWT_SECRET. Sin secreto de firma no se pueden emitir sesiones, y "
        "generarlo al arrancar cerraría la sesión de todo el mundo en cada reinicio. "
        "Genera uno con:  python -c \"import secrets; print(secrets.token_urlsafe(48))\"  "
        "y ponlo en el .env."
    )

# 32 caracteres es poco más de 192 bits en base64url. Un secreto corto convierte la
# firma en algo que se puede romper por fuerza bruta sin prisa.
if len(settings.JWT_SECRET.strip()) < 32:
    raise RuntimeError(
        "JWT_SECRET es demasiado corto: hacen falta al menos 32 caracteres."
    )

# `allow_credentials=True` en app/main.py hace que el navegador rechace un origen `*`,
# pero además un comodín aquí anularía el control de qué frontend puede llamar a la API.
if "*" in settings.ALLOWED_ORIGINS:
    raise RuntimeError(
        "ALLOWED_ORIGINS no puede contener '*': la API se sirve con credenciales "
        "(cabecera Authorization) y necesita una lista explícita de orígenes."
    )
