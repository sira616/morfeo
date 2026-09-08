"""Crea una cuenta desde la consola y genera una contraseña que cumple la política.

    venv\\Scripts\\python.exe scripts/crear_cuenta.py syreta

La contraseña se imprime **una sola vez** y no se guarda en ningún sitio en claro: en
la base de datos solo queda el hash Argon2. Si se pierde, se cambia con
`--reset`, no se recupera.

Se pasa por `auth_service`, no por SQL directo, para que valga exactamente la misma
validación que el registro por la web: usuario normalizado, política de contraseña y
hash idéntico.
"""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core import passwords  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import auth_service  # noqa: E402

# Sin caracteres que se confundan al leerlos en voz alta o al copiarlos de una nota:
# l/1/I, O/0. Una contraseña que se transcribe mal se acaba cambiando por una peor.
LOWER = "abcdefghijkmnopqrstuvwxyz"
UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"
DIGITS = "23456789"
LENGTH = 16


def generate_password() -> str:
    rng = secrets.SystemRandom()
    # Se garantiza una de cada clase y el resto al azar, o la política puede fallar
    # por casualidad justo en la contraseña que acabas de generar.
    chars = [rng.choice(LOWER), rng.choice(UPPER), rng.choice(DIGITS)]
    pool = LOWER + UPPER + DIGITS
    chars += [rng.choice(pool) for _ in range(LENGTH - len(chars))]
    rng.shuffle(chars)
    password = "".join(chars)
    passwords.validate(password)
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description="Crea o reinicia una cuenta de Morfeo.")
    parser.add_argument("username")
    parser.add_argument("--reset", action="store_true", help="Cambia la contraseña si ya existe.")
    args = parser.parse_args()

    password = generate_password()

    with SessionLocal() as db:
        username = auth_service.normalize_username(args.username)
        existing = db.scalar(select(User).where(User.username == username))

        if existing and not args.reset:
            raise SystemExit(f"La cuenta '{username}' ya existe. Usa --reset para cambiarle la clave.")

        if existing:
            existing.password_hash = passwords.hash_password(password)
            db.commit()
            # Cambiar la clave sin cerrar las sesiones abiertas no le quita el acceso a
            # nadie que la tuviera.
            cerradas = auth_service.revoke_all(db, existing)
            print(f"Contraseña de '{username}' cambiada. Sesiones cerradas: {cerradas}.")
        else:
            auth_service.create_user(db, username, password)
            print(f"Cuenta '{username}' creada.")

    print(f"\n  usuario:     {username}")
    print(f"  contraseña:  {password}\n")
    print("Apúntala ahora: no se guarda en claro y no se puede recuperar.")


if __name__ == "__main__":
    main()
