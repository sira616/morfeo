"""Entrega del código de confirmación.

Con SMTP configurado, lo manda. Sin SMTP, lo escribe en la consola del servidor.

Esa segunda vía no es una chapuza: en una app doméstica quien administra el servidor y
quien se registra son la misma persona o están en la misma casa, y la alternativa era
no poder verificar un email nunca. Lo que **no** se hace es devolver el código en la
respuesta HTTP: eso convertiría la verificación en un trámite que cualquiera puede
completar sin acceso al correo, que es justo lo que se quiere impedir.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_verification_code(email: str, code: str) -> bool:
    """True si salió por SMTP; False si se quedó en la consola."""
    body = (
        f"Tu código de confirmación de Morfeo es {code}.\n\n"
        "Caduca en 15 minutos. Si no has pedido nada, ignora este mensaje."
    )

    if not settings.SMTP_HOST.strip():
        print(f"[morfeo] Código de confirmación para {email}: {code}", flush=True)
        return False

    message = EmailMessage()
    message["Subject"] = "Tu código de Morfeo"
    message["From"] = settings.SMTP_FROM
    message["To"] = email
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        return True
    except Exception as exc:
        # Que falle el correo no puede tumbar el registro: el código sigue siendo
        # válido y la consola lo deja recuperable.
        print(f"[morfeo] SMTP falló ({exc}). Código para {email}: {code}", flush=True)
        return False
