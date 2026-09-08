# Morfeo — backend

Recomienda **a qué hora meterte en la cama**, no a qué hora dormirte. Cruza lo que
mide el reloj (sueño, estrés, ejercicio) con lo que solo tú sabes (ánimo, siesta,
café, alcohol) y calcula una ventana, con la explicación de cómo ha salido.

Rama `backend` del repo `morfeo`. El frontend vive en la rama `frontend`.

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
- **Jet lag social**: desfase entre el punto medio de diario y el de viernes y sábado.
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

Con el `.env.example` tal cual (`LOCAL_DEV_AUTH=true`, SQLite) arranca sin Supabase y
sin clave de LLM. La autenticación entonces **no es real**: cualquier email y
contraseña crean cuenta, y el backend se niega a arrancar si eso se combina con
`ENVIRONMENT=production`.

```bash
pytest -q
```

Esperado: **72 passed**, sin red y sin claves.

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
| `POST /api/auth/register` · `login` · `refresh` · `logout` | Supabase Auth |
| `GET`/`PATCH /api/me` | Perfil: hora de despertar, necesidad de sueño, latencia declarada |
| `POST /api/sleep/nights` | Alta de noches. Idempotente por fecha |
| `GET /api/sleep/nights?days=30` | Histórico |
| `POST /api/sleep/import` | Exportación de cualquier reloj (JSON o CSV) |
| `POST /api/sleep/metrics` | Métricas del día: pasos, ejercicio, estrés |
| `PUT /api/checkin` | Check-in por formulario |
| `POST /api/checkin/stream` | Check-in conversacional (SSE) |
| `GET /api/bedtime/tonight` | **La recomendación.** `?wake_target=HH:MM:SS` simula sin guardar |
| `GET /api/insights` | Regularidad, jet lag social, racha, recomendado frente a real y heatmap |
| `GET /api/tips/today` | Cinco consejos con su nivel de evidencia |
| `GET /api/bedtime/history` | Recomendaciones pasadas, con `followed` |
| `PATCH /api/bedtime/{día}/followed` | Marcar si se siguió |

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
