# Morfeo — frontend

Interfaz de Morfeo: te dice **a qué hora meterte en la cama**, no a qué hora dormirte.

Rama `frontend` del repo `morfeo`. El backend vive en la rama `backend`.

---

## Arrancar

```bash
npm install
npm run dev
```

Se abre en `http://localhost:5173` con **MSW respondiendo la API**: no hace falta el
backend, ni Supabase, ni clave de LLM para trabajar en la interfaz. Los datos de
ejemplo están en [`src/mocks/fixtures.ts`](src/mocks/fixtures.ts) y montan a propósito
una racha de eficiencia baja, que es el caso interesante: el que dispara el modo
restricción y el que tardarías dos semanas en reproducir con datos reales.

## Conectar con el backend

La app siempre pide a `/api/...` en su propio origen; es el proxy de Vite quien decide
qué hay detrás. Así el código no sabe si le responde un mock o el backend, y en
desarrollo no hay CORS de por medio.

Crea `.env.local` (no se versiona) con:

```
VITE_API_TARGET=http://127.0.0.1:8000
```

Con esa variable, `npm run dev` **no arranca el servidor de mocks** y manda todo al
backend. Bórrala y vuelves a trabajar sin él. Los dos procesos:

```bash
cd ../morfeo-backend && venv/Scripts/activate && uvicorn app.main:app --reload
```

```bash
npm run dev
```

Comprobación rápida de que el proxy llega al sitio correcto:

```bash
curl -i http://127.0.0.1:5173/api/me
```

Un `401` con la cabecera `server: uvicorn` significa que estás hablando con el backend.
Si no aparece esa cabecera, sigues contra los mocks.

Para un despliegue real, donde el frontend y la API están en dominios distintos, se
usa `VITE_API_BASE_URL` en el build. Ahí sí hay CORS: la URL del frontend tiene que
estar en `ALLOWED_ORIGINS` del backend.

| Comando | Qué hace |
|---|---|
| `npm run dev` | Servidor de desarrollo con mocks |
| `npm run dev:lan` | Igual, pero accesible desde el móvil en la misma wifi |
| `npm run typecheck` | `tsc -b` |
| `npm run lint` | oxlint |
| `npm test` | Vitest (109 tests) |
| `npm run test:e2e` | Playwright sobre el build real |
| `npm run build` | Build de producción |

## Pantallas

| Ruta | Qué hay |
|---|---|
| `/` | **Esta noche**: la ventana, el arco, el resumen del histórico, cinco consejos y el simulador |
| `/anoche` | Apuntar cómo fue la noche, sin necesidad de reloj |
| `/check-in` | El check-in del día, conversando o rellenando |
| `/historial` | Historial denso: gráfica, regularidad, jet lag social, heatmap de ocho semanas y recomendado frente a real |
| `/reloj` | Apuntar la noche y, debajo, conectar o importar del reloj |
| `/perfil` | Horarios, aspecto, cuenta, email opcional y cambio de contraseña |
| `/dev` | Panel de administración. Solo visible para cuentas de `ADMIN_USERNAMES` |
| `/empezar` | Onboarding de tres preguntas |

### Dos formas del mismo shell, no una estirada

En móvil, barra de navegación abajo, donde llega el pulgar. A partir de `lg`, barra
lateral y un lienzo de hasta 1200 px repartido en dos columnas. Una columna de móvil
centrada en un monitor de 1440 px se ve como un teléfono pegado en medio de la
pantalla, y eso no se arregla con padding: se arregla con otro layout y con contenido
que se merezca el ancho.

El reparto de trabajo entre pantallas también es deliberado: la portada respira y dice
una cosa; el historial es denso, porque es donde se miran patrones.

### Se entra con usuario, no con email

La identidad es el nombre de usuario. El email es opcional y el formulario dice para
qué sirve —recuperar la contraseña— en vez de dejar que se adivine.

Cambiar la contraseña cierra **todas** las sesiones, también la de la pestaña donde se
cambia: el backend revoca los refresh, así que quedarse ahí solo llevaría al siguiente
401. La pantalla lo avisa antes y devuelve al login al terminar.

### El color tiene una regla

**Si se puede pulsar, indigo. Si te informa de cómo va la cosa, verde.** Los tokens
`--mf-good*` y `--mf-chart-*` de [tokens.css](src/styles/tokens.css) existen para que
esa regla se cumpla sola en vez de depender de que cada componente la recuerde.

El verde es un menta (`#4fd6a0`) que da 9,85:1 sobre las tarjetas, así que vale también
como texto; el lima que venía de Plátano era de bebida energética. Hay un test de
contraste que guarda la paleta entera contra WCAG AA.

### La pantalla principal no da solo una hora

Da una **ventana** (±20 min), porque una hora al minuto sería precisión falsa, y
debajo el desglose completo: cada factor con sus minutos y su motivo. El backend
manda esa lista ya calculada; aquí solo se pinta. Si un día el desglose no cuadra con
la hora, el fallo está en el motor, no en esta capa.

### El desglose vive detrás de una pregunta

«¿Por qué esta hora?» abre una ventana con los factores, las notas y la confianza. Es
información que se consulta cuando te lo preguntas, no cada vez que abres la app, y
tenerla siempre desplegada competía con la única cifra que importa. Su sitio lo ocupa
ahora el resumen del histórico, que contesta «¿cómo voy?».

La ventana usa `<dialog>` nativo: `showModal()` trae gratis el foco atrapado dentro,
cerrar con Escape y el resto de la página inerte para lectores de pantalla. Lleva un
respaldo para entornos sin esa API, donde se abre como diálogo normal.

### Apuntar la noche sin reloj

No se pregunta cuántos minutos dormiste, porque nadie lo sabe. Se piden las horas de
acostarse y levantarse, lo que tardaste en dormirte y el rato que estuviste despierta,
y de ahí salen el tiempo en la cama y el sueño total. Es la cuenta que hace un reloj,
con datos que una persona sí puede responder, y el resultado se enseña **antes** de
guardar: si sale algo raro se ve ahí y no tres pantallas después en una media.

Está en `/anoche`, encadenado a marcar si seguiste la recomendación, y también arriba
del todo en `/reloj`: sin reloj es la única forma de que el motor conozca tu latencia y
tu eficiencia reales, así que va antes que lo opcional.

### El arco de la noche

Las franjas del arco son proporcionales al tiempo real: el trozo ámbar del principio es
lo que tardas en dormirte, y verlo aparte del verde es lo que mete en la cabeza la idea
que la app defiende. SVG a mano, sin librería: son tres segmentos de círculo.

### Los consejos enseñan su nivel de evidencia

Cinco al día, priorizando lo que hoy te viene a cuento (café tarde, eficiencia baja,
horario irregular) y estables durante la jornada, para que se lean en vez de hojearse.
Cada uno lleva su fuente y si la evidencia es alta, media o limitada.

Esa etiqueta no es adorno. La AASM recomienda no usar la higiene del sueño como
tratamiento único del insomnio, así que presentar "ventila la habitación" con el mismo
peso que "reserva la cama para dormir" sería mentir por omisión. El corpus y la
selección viven en el backend, donde tienen tests.

### El check-in tiene dos caras

Conversando es lo bonito, pero hay noches en que nadie quiere hablar con una app.
El formulario escribe exactamente los mismos campos, así que perder el dato por no
tener ganas de conversar habría sido absurdo.

## Instalarla en el iPhone

La app se añade a la pantalla de inicio y se abre a pantalla completa, sin barra de
Safari. No hace falta App Store ni código nativo.

Con el backend levantado en el portátil:

```bash
npm run dev:lan
```

Busca la IP local del portátil (`ipconfig` en Windows, la línea *Dirección IPv4* del
adaptador de la wifi) y abre `http://esa.ip:5173` en **Safari** del iPhone. Compartir →
*Añadir a pantalla de inicio*.

El backend puede seguir escuchando en `127.0.0.1`: el proxy corre en el portátil, así
que el móvil solo habla con Vite.

### Conectar la API real desde el iPhone

`npm run dev:lan` abre Vite a la wifi, nada más. Que el móvil pinte datos no significa
que esté hablando con el backend: sin `VITE_API_TARGET` arranca el servidor de mocks y
el iPhone muestra las fixtures tan contento. Es el error fácil de cometer aquí, porque
la app se ve perfecta y los números son inventados.

Tres pasos, en este orden:

1. `.env.local` con `VITE_API_TARGET=http://127.0.0.1:8000`. Sin esa línea, mocks.

2. El backend levantado:

   ```bash
   cd ../morfeo-backend && venv/Scripts/activate && uvicorn app.main:app --reload
   ```

3. Vite abierto a la wifi:

   ```bash
   npm run dev:lan
   ```

Al arrancar, Vite imprime `API → http://127.0.0.1:8000 (backend real, mocks
desactivados)`. Si esa línea no sale, estás contra los mocks y no hace falta seguir
mirando.

**El backend no se toca.** Sigue escuchando en `127.0.0.1:8000` y `ALLOWED_ORIGINS` se
queda como está. El iPhone solo habla con Vite, y es Vite quien reenvía `/api` desde el
portátil: para Safari todo viene del mismo origen, así que no hay CORS que configurar.
Levantar uvicorn con `--host 0.0.0.0` expondría la API a la wifi entera sin ganar nada
a cambio.

**Hay que abrir el puerto en el firewall de Windows.** Que Vite escuche en `0.0.0.0` no
basta: el firewall corta la conexión entrante y en el iPhone se ve como una página que
no carga, sin ningún mensaje que lo explique. Una vez, en PowerShell como
administrador:

```powershell
netsh advfirewall firewall add rule name="Vite 5173" dir=in action=allow protocol=TCP localport=5173
```

Para comprobar que el móvil llega y que detrás hay backend, lánzalo desde el portátil
contra la IP de la wifi, no contra `localhost`:

```bash
curl -i http://192.168.1.42:5173/api/me
```

Un `401` con la cabecera `server: uvicorn` confirma las dos cosas a la vez: el puerto
está abierto y quien responde es el backend. Los mocks devuelven ese mismo `401`, así
que la cabecera es lo único que los distingue.

La IP cambia cuando el router renueva el DHCP, y entonces el icono de la pantalla de
inicio apunta a una dirección muerta. Si la app deja de cargar de un día para otro,
mira la IP antes que nada; reservarla en el router es lo que evita reinstalar el acceso
directo cada pocas semanas.

Lo que hace que se vea como una app y no como una web: `viewport-fit=cover` y las
clases `safe-*` de [src/index.css](src/index.css), que devuelven el hueco del notch y
del indicador de inicio; las metas `apple-mobile-web-app-*` de
[index.html](index.html), que iOS lee en vez del manifest; y un
[manifest](public/manifest.webmanifest) con `display: standalone`. Hay un test que
guarda todo eso, porque si alguien borra una meta la web sigue funcionando y solo se
nota al reinstalarla en el móvil.

### Lo que esto NO resuelve

- **Solo funciona con el portátil encendido y en la misma wifi.** Para usarla fuera de
  casa hace falta desplegarla.
- **No lee la app Salud.** HealthKit no es accesible desde una web: ninguna PWA puede
  leer tu sueño. La vía sin código nativo es una automatización de Atajos que haga
  `POST` a `/api/sleep/nights` cada mañana. Mientras tanto, el check-in manual y el
  importador.
- **Sin notificaciones.** iOS las permite a las PWA instaladas, pero exigen HTTPS, así
  que llegan con el despliegue, no con esto.
- **Pide contraseña cada vez** que iOS descarga la app de memoria: los tokens viven
  solo en memoria, por decisión deliberada.

## Stack

React 19 · Vite · TypeScript · Tailwind 4 · Zustand · TanStack Query · React Router ·
MSW · Vitest + Testing Library · Playwright.

Los tokens de diseño viven en [`src/styles/tokens.css`](src/styles/tokens.css) con
prefijo `--mf-`. El tema arranca en oscuro por decisión de producto: la app se abre de
noche, y un fogonazo blanco a las once es justo lo contrario de lo que recomienda.

## Detalles que conviene no deshacer

**Se persiste solo el refresh token**, nunca el access ni el perfil. Antes no se
guardaba nada y recargar cerraba la sesión, que en una app añadida a la pantalla de
inicio del móvil es insufrible: iOS la descarga de memoria constantemente.

El precio es que ese token sobrevive a cerrar el navegador. Se acota guardando el de
menor valor posible —el access caduca en media hora y no hace falta persistirlo—,
rotándolo en cada uso y pudiendo revocarlo desde el servidor, que es justo lo que un
access sin estado no permite. `RequireAuth` espera a que termine la restauración antes
de decidir, o recargar una ruta protegida rebotaría al login antes de tiempo.

**MSW se carga con `import()` dinámico** en [`src/mocks/browser.ts`](src/mocks/browser.ts).
Cargarlo en el nivel del módulo metía la librería de mocks y los datos de ejemplo en
el bundle de producción: 764 kB frente a los 339 kB de ahora.

**La gráfica del historial es SVG a mano.** Son dos series y treinta barras; una
librería de charting pesaría más que la página entera.

**Para márgenes y rellenos se usa la escala numérica de Tailwind** (`p-4`, `gap-2`,
`px-6`), no alias con nombre. La plantilla de origen definía `--spacing-sm: 12px` y
compañía, y Tailwind resuelve `max-w-sm` contra la escala de espaciado antes que
contra la de anchos: `max-w-sm` valía 12px y cualquier tarjeta centrada salía como un
hilo de píxeles. El único alias que queda es `--spacing-touch` (44px, objetivo táctil
mínimo), que no colisiona con nada.

**El modo noche profunda no es «el oscuro pero más oscuro».** El tema oscuro normal
pone el texto a 17:1 sobre su fondo, que a las doce de la noche es un flash; en `.noche`
va a 8.8:1, de sobra para leer y lejos de deslumbrar. No queda ni un blanco ni un azul,
y esto último no es estética: la luz de longitud de onda corta es la que más frena la
melatonina, así que un tema para leer en la cama que mantuviera el índigo de los botones
estaría contradiciendo lo que la propia app recomienda.

El precio hay que decirlo. El resto de la interfaz usa el color como regla —índigo si
se puede pulsar, verde si te informa— y con un solo tono disponible esa regla no cabe.
Se mantiene con otra cosa: lo pulsable va **relleno** de ámbar con texto oscuro encima,
lo informativo va en ámbar apagado como texto o borde. Los contrastes están fijados en
[`tests/unit/wcagContrast.test.ts`](tests/unit/wcagContrast.test.ts), **con techo además
de suelo**: sin el techo, cualquier «se lee poco, lo subo un pelo» devolvería el tema al
punto de partida sin que ningún test se quejara, porque subir el contraste nunca rompe
AA.

Se enciende solo de 22:00 a 6:00 (`autoNoche`, en `uiStore`). Elegir tema a mano lo
apaga: si no, la app te lo cambiaría por debajo al minuto siguiente y parecería que no
hace caso al botón.

**El simulador distingue «Hoy» de «0».** Los controles son fichas y no cajas de número
por eso mismo: una ficha puede decir «Hoy» y otra «Ninguno», y se ve cuál está puesta
sin leer nada. En cuanto hay algo simulado desaparece el botón de «la seguí» —marcar
como seguida una hora inventada ensuciaría justo el dato con el que se comprueba si el
motor acierta— y la cifra se acompaña de cuánto se ha movido respecto a la real, que es
lo que hace que se entienda: una hora suelta no dice nada, «20 min antes» sí.

## Pendiente

- Sin CI.
- Sin tests de accesibilidad automatizados (la plantilla trae `vitest-axe` y
  `@axe-core/playwright` instalados, pero todavía sin usar).
- El desglose de factores no está traducido a gráfico; hoy es una lista.
- El simulador solo mueve la hora de despertar; falta poder mover cafeína, siesta y
  ejercicio para ver la hora reaccionar en vivo.
- Sin notificación ni recordatorio a la hora de la ventana, que es la funcionalidad
  que haría que la app se use sin abrirla. Requiere despliegue con HTTPS.
- Sin despliegue: hoy solo se usa desde la wifi de casa con el portátil encendido.
- Sin entrada automática de datos desde el iPhone (ver el apartado de arriba).
