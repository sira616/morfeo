# Morfeo — backend

Recomienda **a qué hora meterte en la cama**, no a qué hora dormirte. Cruza lo que
mide el reloj (sueño, estrés, ejercicio) con lo que solo tú sabes (ánimo, siesta,
café, alcohol) y calcula una ventana, con la explicación de cómo ha salido.

Rama `backend` del repo `morfeo`. El frontend vive en la rama `frontend`, en la carpeta
de al lado.

> **Este clon solo conoce la rama `backend`.** Las dos carpetas son clones del mismo
> repositorio, una por rama, y cambiar de rama aquí sustituía todo el backend por el
> frontend: pasó dos veces, la segunda desde GitHub Desktop. No se perdía nada, pero el
> susto y los 5000 ficheros «sin commitear» del `venv` no compensan.
>
> Ahora `git checkout frontend` falla con *pathspec did not match*, porque el refspec
> del remoto está acotado:
>
> ```bash
> git config remote.origin.fetch "+refs/heads/backend:refs/remotes/origin/backend"
> ```
>
> Para trabajar en el frontend, la carpeta de al lado. Si algún día hace falta la otra
> rama aquí, se revierte poniendo `+refs/heads/*:refs/remotes/origin/*`.

---

## La decisión de diseño que lo ordena todo

**El LLM no calcula.** Entrevista y explica; los minutos los pone
[`app/domain/bedtime.py`](app/domain/bedtime.py), una función pura sin base de datos,
sin red y sin reloj del sistema.

Un modelo haciendo aritmética sobre deuda de sueño y latencia de conciliación da un
resultado distinto cada vez, no se puede testear y no puede justificar por qué dijo
las 23:40. Con el motor separado hay tests deterministas, la misma entrada da siempre
la misma hora, y cada recomendación viene con la lista de factores que la componen.

El corolario práctico: si un día quieres cambiar el modelo, o quitarlo, la app sigue
funcionando. Solo pierde la conversación.

## Qué hace el motor

```
objetivo = necesidad basal
         + recuperación de deuda (25% de la deuda, máximo 60 min)
         + ajuste por estrés y por carga de ejercicio
         - la mitad de la siesta de hoy
objetivo = recortado al rango 6-10 h

tiempo en cama = objetivo / eficiencia observada
hora de acostarse = hora de despertar - tiempo en cama - latencia de conciliación
```

Tres cosas que lo separan de una calculadora de "ocho horas antes de la alarma":

**La latencia de conciliación se descuenta.** Si tardas 45 minutos en dormirte,
"acuéstate a las 23:00 para dormir ocho horas" te está pidiendo siete y cuarto. Ese
descuento es la razón de ser de la app.

**La deuda se paga a plazos.** Dormir tres horas de más una noche desplaza el ritmo
circadiano y empeora la siguiente. Se recupera un 25% por noche, con tope de una hora.

**Con la eficiencia baja, la ventana se acorta.** Es contraintuitivo y deliberado. Por
debajo del 85% de eficiencia (dormido frente a tiempo en la cama) el problema no es
falta de oportunidad para dormir: es que la cama se está usando para estar despierto.
Ampliar la ventana refuerza esa asociación. El motor entra en modo `restriccion` y
comprime a lo que la persona duerme de verdad más 30 minutos, con un suelo de 5 h 30.
Es la base de la restricción de sueño de la TCC-I.

**El ejercicio de tarde no penaliza.** La ventana era de tres horas y bajó a una, y
solo para el vigoroso: un metaanálisis de 23 estudios no encontró diferencias en
latencia, eficiencia ni duración con ejercicio vespertino, y la única excepción es el
intenso que acaba a menos de una hora, que retrasa el inicio unos catorce minutos.
Penalizar a tres horas desaconsejaba entrenar por la tarde sin motivo, que es un mal
consejo de salud.

Cada regla lleva su test en [`tests/test_bedtime.py`](tests/test_bedtime.py).

## Métricas del histórico

[`app/domain/insights.py`](app/domain/insights.py) es igual de puro que el motor, y usa
**estadística circular** en casi todo. No es un capricho: el punto medio de sueño de
quien se acuesta a las 00:30 vale 30 minutos y el de quien se acuesta a las 23:30 vale
1410; su media aritmética da las doce del mediodía, que es absurdo. En el círculo da la
medianoche.

- **Regularidad**: dispersión del punto medio de sueño, llevada a una puntuación de 0 a
  100. En 61.000 adultos del UK Biobank, el quintil más regular tuvo un 30% menos de
  mortalidad por cualquier causa, y la regularidad predijo mejor que las horas dormidas.
- **Qué acompaña a tus mejores noches**: compara las noches con cada hábito (alcohol,
  café tarde, ejercicio…) contra las noches sin él. Sustituyó al jet lag social, que
  era una media de población; esto habla de los datos de quien mira. Solo se enseña con
  al menos tres noches a cada lado y veinte minutos de diferencia: por debajo es ruido,
  y enseñarlo invita a concluir.
- **Racha y adherencia**: noches siguiendo la recomendación. Un día sin responder no
  rompe la racha; castigar el olvido convertiría la racha en una obligación de
  registrar, que es el tipo de presión que estropea el sueño.

Cuando faltan noches con horas reales, estas métricas devuelven `null`, nunca un cero:
un cero se leería como "tienes un horario malísimo" cuando lo que pasa es que el
importador solo trajo duraciones.

## Consejos

[`app/content/sleep_tips.py`](app/content/sleep_tips.py) es un corpus de treinta y pico
consejos, cada uno con **nivel de evidencia y fuente**, y las dos cosas se enseñan.

Es una decisión de producto, no un adorno: la AASM recomienda no usar la higiene del
sueño como terapia única para el insomnio crónico, porque los consejos sueltos no son
un tratamiento. Lo que tiene respaldo fuerte es la parte conductual —control de
estímulos y restricción de sueño— que es la que ya aplica el motor. Una app que
presenta "ventila la habitación" con el mismo peso que "reserva la cama para dormir"
está mintiendo por omisión.

La selección de cada día prioriza lo que le pasa hoy a esa persona (café tarde,
alcohol, eficiencia baja, horario irregular) y se siembra con `(usuario, fecha)`, así
que no cambia al recargar: unos consejos que bailan no se leen, se hojean.

## Arrancar

Requiere Python 3.11.

```bash
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Hace falta un `JWT_SECRET` en el `.env` o el backend no arranca. Se genera con:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

No se genera solo al arrancar a propósito: un secreto nuevo invalida las firmas
anteriores, así que cerraría la sesión de todo el mundo en cada reinicio, que es justo
lo que este despliegue evita.

```bash
pytest -q
```

Esperado: **141 passed**, sin red y sin claves.

## Conectar con el frontend

El frontend pide siempre a `/api/...` en su propio origen y el proxy de Vite decide
qué hay detrás, así que en desarrollo no hay CORS. En la rama `frontend`, un
`.env.local` con:

```
VITE_API_TARGET=http://127.0.0.1:8000
```

hace que `npm run dev` deje de levantar los mocks y hable con este backend. Levanta
los dos y comprueba que llegan:

```bash
curl -i http://127.0.0.1:5173/api/me
```

`401` con la cabecera `server: uvicorn` significa que el proxy llega aquí.

En un despliegue real, con dominios distintos, el frontend usa `VITE_API_BASE_URL` y
entonces sí interviene CORS: su URL tiene que estar en `ALLOWED_ORIGINS`, sin comodines
(el arranque falla si los hay).

## Rutas

| Ruta | Qué hace |
|---|---|
| `POST /api/auth/register` · `login` · `refresh` · `logout` | Autenticación local con JWT |
| `POST /api/auth/change-password` | Cambia la clave y cierra todas las sesiones |
| `POST /api/auth/email` · `email/verify` | Añadir email y confirmarlo con un código |
| `GET`/`PATCH /api/me` | Perfil: hora de despertar, necesidad de sueño, latencia declarada |
| `POST /api/sleep/nights` | Alta de noches. Idempotente por fecha |
| `GET /api/sleep/nights?days=30` | Histórico |
| `POST /api/sleep/import` | Exportación de cualquier reloj (JSON o CSV) |
| `POST /api/sleep/metrics` | Métricas del día: pasos, ejercicio, estrés |
| `PUT /api/checkin` | Check-in por formulario |
| `GET /api/checkin/recent` | Últimos check-ins, para el resumen de la portada |
| `POST /api/checkin/stream` | Check-in conversacional (SSE) |
| `GET /api/bedtime/tonight` | **La recomendación.** `?wake_target=HH:MM:SS` simula sin guardar |
| `GET /api/insights` | Regularidad, asociaciones, racha, recomendado frente a real y heatmap |
| `GET /api/tips/today` | Cinco consejos con su nivel de evidencia |
| `GET /api/dev/users` · `users/{id}` | Panel de administración. Responde 404 a quien no es admin |
| `GET /api/bedtime/history` | Recomendaciones pasadas, con `followed` |
| `PATCH /api/bedtime/{día}/followed` | Marcar si se siguió |

## Usarlo desde el móvil en casa

El backend sirve también el frontend construido, así que hay **una sola URL y un solo
proceso**. No hay dos servidores ni proxy que mantener, y como todo viene del mismo
origen, tampoco hay CORS.

```bash
cd ../morfeo-frontend && npm run build
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar-arranque.ps1
```

Eso registra una tarea programada que arranca Morfeo al iniciar sesión, así que
sobrevive a un reinicio. Tarea de usuario y no servicio de Windows: un servicio
necesitaría permisos de administrador y correría sin tu perfil, que es más de lo que
hace falta para una app doméstica.

Falta una cosa que sí necesita administrador, y es la que más despista si se olvida:

```powershell
New-NetFirewallRule -DisplayName 'Morfeo' -Direction Inbound -Action Allow `
  -Protocol TCP -LocalPort 8000 -Profile Private
```

Sin esa regla el móvil no conecta y la página simplemente no carga, sin ningún mensaje
que lo explique.

### La dirección

`http://syreta.local:8000` es la buena: Windows responde a mDNS con el nombre del
equipo y el iPhone lo resuelve por Bonjour, así que sigue funcionando aunque el router
cambie la IP. La IP directa (`http://192.168.1.19:8000`) funciona también, pero es la
que se rompe sola de un día para otro.

Un aviso: si el equipo tiene adaptadores virtuales (VirtualBox, Hyper-V, WSL), mDNS
anuncia **todas** sus IPs y el móvil puede intentar primero una que no alcanza. Si
tarda en cargar, la IP directa lo descarta enseguida.

### Reiniciar el servidor

```powershell
powershell -ExecutionPolicy Bypass -File scripts
einiciar.ps1
```

Y no `Stop-ScheduledTask` a secas: no siempre se lleva por delante al uvicorn, el
arranque nuevo no puede enlazar el puerto y muere en silencio. El resultado es el peor
posible, porque el servidor responde —el viejo— y parece que el reinicio ha funcionado
mientras sigue sirviendo el código anterior. El script mata por puerto.

### Datos de ejemplo

```bash
venv\Scripts\python.exe scripts/sembrar_demo.py tu@email.com
```

Escribe en la base de datos y no por la API a propósito: sesenta noches seguidas por
HTTP chocan con el rate limiting, que está ahí por buenos motivos.

## Autenticación

Local, sin proveedor externo. **La identidad es el nombre de usuario**, no el email:
esto se usa entre un par de personas en una red doméstica, y pedir un correo para
entrar en tu propia app de sueño no aporta nada.

El email es opcional y sirve para una sola cosa: recuperar la contraseña. Mientras no
se verifique, la cuenta funciona igual. Una cuenta sin email nace verificada, porque no
tiene nada que verificar y arrastrar un aviso que no se puede quitar sería absurdo.

- **Contraseñas** con Argon2id, no bcrypt: es lo que recomienda OWASP y no trunca en
  silencio a 72 bytes. Política de 12 caracteres con mayúscula, minúscula y número;
  **sin exigir carácter especial**, porque empuja a `Contraseña1!` y la longitud es lo
  que de verdad cuesta de adivinar.
- **JWT propio**: access de 30 minutos sin estado, y refresh de 30 días **con** estado.
  El `jti` del refresh vive en `refresh_tokens`, y sin esa tabla cerrar sesión sería
  una mentira. Al refrescar se rota y se anula el anterior: sin rotación, un refresh
  robado sirve un mes en paralelo a la sesión legítima.
- El `type` va en las claims. Sin él, un refresh serviría como access y duraría treinta
  días en vez de treinta minutos.
- Entrar con usuario inexistente y con contraseña mala dan **el mismo mensaje**:
  distinguirlos convierte el formulario en un buscador de cuentas.
- El código de confirmación **no viaja en la respuesta HTTP**. Si lo hiciera, verificar
  un email sería un trámite que cualquiera completa sin acceso a ese correo. Sin SMTP
  configurado sale por la consola del servidor.

### Cuentas

```bash
venv\Scripts\python.exe scripts/crear_cuenta.py syreta
venv\Scripts\python.exe scripts/crear_cuenta.py syreta --reset
```

Genera una contraseña que cumple la política y la imprime **una sola vez**: en la base
de datos solo queda el hash. Si se pierde, se cambia; no se recupera.

## Panel de /dev

Quién se ha registrado, cuánto registra cada uno y un diario de acciones por usuario.
Las cuentas con acceso salen de `ADMIN_USERNAMES`; el rol **nunca** llega del cliente y se
recalcula en cada petición, así que quitar a alguien de la lista le quita el acceso sin
tocar la base de datos.

A quien no es admin le responde **404**, no 403: un 403 confirma que la ruta existe y
que hay algo detrás que merece la pena buscar.

El registro guarda qué acción hizo cada persona y qué campos tocó, **nunca lo que
escribió**. Hay un test que lo comprueba metiendo un secreto en las notas de un
check-in y mirando que no aparezca por ninguna parte del panel.

## Relojes

Todo lo que entra pasa por [`app/wearables/base.py`](app/wearables/base.py) antes de
tocar la base de datos, así que cambiar de reloj no obliga a tocar el cálculo.

| Proveedor | Estado | Cómo |
|---|---|---|
| `import` | Listo | Exportación JSON o CSV. Funciona con cualquier reloj desde el primer día |
| `manual` | Listo | `POST /api/sleep/nights` |
| `oura` | Listo | Personal Access Token, sin OAuth ni aprobación |
| `fitbit` | Pendiente | OAuth2 con PKCE, cuenta de desarrollador gratuita |
| `garmin` | No planificado | Su Health API exige aprobación como socio; hasta entonces, exportar de Garmin Connect |

Empieza por `import`: te da datos con los que trabajar hoy y no depende de que ninguna
API te apruebe.

## Seguridad

Heredada de la plantilla de la que sale este repo, y aquí importa más: esto son datos
de salud.

- Rate limiting por IP y ruta en todo lo que emite credenciales, cuesta dinero o
  escribe filas.
- Fail-fast de configuración: no arranca con Supabase mal configurado, con `*` en
  `ALLOWED_ORIGINS`, ni con `LOCAL_DEV_AUTH` en producción.
- `/docs` fuera de producción.
- Longitudes máximas y rangos en cada esquema de entrada.
- Toda consulta filtra por `user_id`; una fila ajena responde 404, no 403.
- Lo que devuelve el LLM pasa por el mismo esquema Pydantic que el formulario: un
  modelo que aluciné `nap_minutes: 900` se queda fuera.

### Lo que no está cubierto

- **El rate limiting vive en memoria de un proceso.** Con varios workers cada uno
  lleva su cuenta. Correcto para un despliegue de un proceso; al escalar, a Redis.
- **Sin CI.** Los 43 tests no los ejecuta nadie automáticamente todavía.
- **Sin cifrado en reposo** más allá del que dé el motor de base de datos.
- **Sin migraciones.** `create_all` al arrancar; un cambio de columna en una tabla
  existente hay que aplicarlo a mano.
- **Sin borrado de cuenta ni exportación de datos propios**, que en datos de salud
  debería estar.

## Aviso

Morfeo es una herramienta de hábitos, no un dispositivo médico, y no diagnostica nada.
El insomnio persistente lo valora un profesional del sueño.
