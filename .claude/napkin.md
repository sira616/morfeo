# Napkin — morfeo (rama `backend`)

Runbook curado del repo. No es un diario de sesión: solo lo que se repite.

## Trampas del entorno (leer antes de tocar nada)

1. **Esta carpeta es solo la rama `backend`.** El frontend vive en
   `../morfeo-frontend`, que es otro clon del mismo repo apuntando a `frontend`.
   `git checkout frontend` aquí sustituye todo el backend por el frontend: ha pasado
   dos veces. El README documenta un refspec acotado como guardia
   (`git config remote.origin.fetch "+refs/heads/backend:refs/remotes/origin/backend"`),
   pero **a día de hoy este clon tiene `+refs/heads/*` y una rama local `frontend`**,
   así que la guardia no está puesta.
2. **Windows + PowerShell 5.1.** Sin `&&`, sin `??`, sin ternario. Encadenar con
   `;` o `if ($?) { ... }`. Python es `venv\Scripts\python.exe`.
3. **`.env` no se commitea y `JWT_SECRET` es obligatorio**: sin él el backend no
   arranca (fail-fast en `app/core/config.py`). Mínimo 32 caracteres.
4. **Reiniciar el servidor con `scripts\reiniciar.ps1`**, nunca con
   `Stop-ScheduledTask` a secas: el uvicorn viejo sigue escuchando y el nuevo muere
   en silencio mientras el anterior responde con el código antiguo.
5. **`morfeo.local` lo anuncia la propia app por mDNS** (`app/core/mdns.py`, activo
   cuando `MDNS_NAME` está puesto; lo pone `scripts\morfeo.ps1`). El fichero `hosts`
   NO sirve para esto: solo lo lee este ordenador y hay que resolverlo en el iPhone.
   El nombre mDNS que Windows da por su cuenta es `DESKTOP-LC1P85F.local`.
6. **La wifi estaba marcada como Pública**, así que las reglas de firewall con
   `-Profile Private` no aplicaban. `scripts\abrir-en-la-wifi.ps1` (admin) lo corrige
   y abre 8000/TCP y 5353/UDP. Sin el 5353 el nombre no resuelve desde el móvil y
   parece un fallo del servidor.

## Cómo se levanta todo

```powershell
python -m venv venv; .\venv\Scripts\python.exe -m pip install -r requirements.txt
# .env con JWT_SECRET
cd ..\morfeo-frontend; npm ci; npm run build
# y luego, desde morfeo\:
$env:FRONTEND_DIST = "C:\Users\Sira\Documents\GitHub\morfeo-frontend\dist"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Un solo proceso sirve API y frontend, así que no hay CORS. `pytest -q` → 180 passed,
sin red y sin claves. El build del frontend tarda ~5 s; `npm ci` unos minutos.

## Invariantes de diseño que no hay que romper

1. **El LLM no calcula.** Los minutos salen de `app/domain/bedtime.py`, función pura.
   Si una tarea empieza a pedirle aritmética al modelo, es que va mal encaminada.
2. **`GET /api/bedtime/tonight` solo guarda si NO hay parámetros de simulación.**
   Fijado en `tests/test_simulador.py`. Guardar una simulación arruina el histórico.
3. **`None` ≠ `0` en el simulador.** Omitir = «usa lo de hoy»; `0` = «simula que no
   hubo». Por eso todo es opcional sin valor por defecto.
4. **El rol de admin nunca llega del cliente**: se recalcula en cada petición desde
   `ADMIN_USERNAMES`. A quien no es admin, `/api/dev` responde 404, no 403.
5. **La salida del LLM pasa por el mismo Pydantic que el formulario** (`CheckinIn`),
   con lista blanca de campos en `checkin_service.EXTRACTABLE_FIELDS`.
6. **Las métricas devuelven `null`, nunca `0`, cuando faltan datos.** Un cero se lee
   como «tienes un horario malísimo».
7. **El auditor guarda qué acción, nunca qué se escribió.** Hay un test que mete un
   secreto en las notas y comprueba que no aparece en `/dev`.
8. **Un email sin verificar no es una identidad**: `find_by_login` solo empareja por
   email si `email_verified`. La recuperación de contraseña se construirá encima.
9. **Las dos ramas del login gastan el mismo Argon2** (`passwords.verify_dummy`). El
   mensaje único no vale de nada si el cronómetro las separa.
10. **`scripts\morfeo.ps1` fuerza `ENVIRONMENT=production`** porque es el arranque que
    escucha en `0.0.0.0`: cierra `/docs` y `/openapi.json`. En desarrollo contra
    `127.0.0.1` manda el `.env` y `/docs` sigue disponible.

## mDNS (`app/core/mdns.py`)

Dos cosas que costaron encontrar y que no dan un mensaje útil al fallar:

- **Hay que usar la API asíncrona** (`AsyncZeroconf` + `await async_register_service`).
  La síncrona bloquea el bucle de asyncio desde el lifespan de FastAPI y aborta con
  `EventLoopBlocked` **y el mensaje vacío**.
- **`cooperating_responders=True`** es obligatorio aquí: en este equipo corre además
  el mDNSResponder de Apple, y al reiniciar el proceso anterior nunca retira su
  anuncio (se mata por puerto), así que el nombre siempre aparece reclamado. Sin esa
  bandera, el registro falla con otra excepción de mensaje vacío.

Al registrar un fallo de zeroconf, imprimir `type(exc).__name__`: solo con `str(exc)`
la línea sale como «no se pudo anunciar ()».

Para comprobar qué se está anunciando de verdad, un `ServiceBrowser` sobre
`_http._tcp.local.` enseña nombre, `server` y la IP. Es la única prueba fiable: que
`morfeo.local` responda en este PC no garantiza que el móvil lo vea.

## CSP

`app/core/headers.py`. `script-src 'self'` es lo que protege el refresh token que el
frontend guarda en `localStorage`; `style-src` lleva `'unsafe-inline'` porque la
interfaz usa `style={{…}}` de React en treinta componentes. `/docs` y `/redoc` quedan
exentos de CSP porque Swagger carga su JS de un CDN.

Al tocarla, comprobar en el navegador de verdad y no solo con los tests: una CSP mal
puesta no rompe nada en `TestClient`, solo en la página.

## Cambiar un modelo

```powershell
.\venv\Scripts\python.exe -m alembic revision --autogenerate -m "qué cambia"
```

Revisar el fichero: autogenerate no adivina un renombrado, propone borrar y crear, y
eso pierde datos. `tests/test_migrations.py` falla si hay modelo sin migración.

## Deuda conocida, por orden

1. **Todo va por HTTP.** Contraseñas, refresh de 30 días y datos de salud en claro por
   la wifi. Es el mismo trabajo que piden las notificaciones del frontend.
2. Sin CI: los 188 tests no los corre nadie.
3. Sin borrado de cuenta ni exportación (`DELETE /api/me`, `GET /api/me/export`). Es
   lo único de la lista que con datos de salud no es opcional.
4. El rate limiter no libera claves nunca; sin tope de tamaño de cuerpo.
5. Frontend: la deuda de sueño y el informe semanal son backend hecho esperando
   pantalla (`sleep_debt` en `/api/bedtime/tonight`, `/api/insights/weekly`).

## Documentación desfasada (revisar al pasar por ahí)

- `../morfeo-frontend/README.md` dice `cd ../morfeo-backend`, pero la carpeta del
  backend se llama `morfeo`.
