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
| `npm run typecheck` | `tsc -b` |
| `npm run lint` | oxlint |
| `npm test` | Vitest (50 tests) |
| `npm run test:e2e` | Playwright sobre el build real |
| `npm run build` | Build de producción |

## Pantallas

| Ruta | Qué hay |
|---|---|
| `/` | **Esta noche**: la ventana, el desglose de factores y el simulador de "¿y si mañana madrugo?" |
| `/check-in` | El check-in del día, conversando o rellenando |
| `/historial` | Últimas 30 noches, con gráfica y eficiencia |
| `/reloj` | Importar la exportación del reloj |
| `/perfil` | Hora de despertar, necesidad de sueño, latencia |
| `/empezar` | Onboarding de tres preguntas |

### La pantalla principal no da solo una hora

Da una **ventana** (±20 min), porque una hora al minuto sería precisión falsa, y
debajo el desglose completo: cada factor con sus minutos y su motivo. El backend
manda esa lista ya calculada; aquí solo se pinta. Si un día el desglose no cuadra con
la hora, el fallo está en el motor, no en esta capa.

### El check-in tiene dos caras

Conversando es lo bonito, pero hay noches en que nadie quiere hablar con una app.
El formulario escribe exactamente los mismos campos, así que perder el dato por no
tener ganas de conversar habría sido absurdo.

## Stack

React 19 · Vite · TypeScript · Tailwind 4 · Zustand · TanStack Query · React Router ·
MSW · Vitest + Testing Library · Playwright.

Los tokens de diseño viven en [`src/styles/tokens.css`](src/styles/tokens.css) con
prefijo `--mf-`. El tema arranca en oscuro por decisión de producto: la app se abre de
noche, y un fogonazo blanco a las once es justo lo contrario de lo que recomienda.

## Detalles que conviene no deshacer

**Los tokens viven solo en memoria**, nunca en `localStorage`. Aquí hay datos de sueño
y de estado de ánimo; un token persistido sobrevive a cerrar el navegador en un
ordenador compartido.

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

## Pendiente

- Sin CI.
- Sin tests de accesibilidad automatizados (la plantilla trae `vitest-axe` y
  `@axe-core/playwright` instalados, pero todavía sin usar).
- El desglose de factores no está traducido a gráfico; hoy es una lista.
- Sin notificación ni recordatorio a la hora de la ventana, que es la funcionalidad
  que haría que la app se use sin abrirla.
