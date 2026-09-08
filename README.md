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

Para apuntar al backend de verdad, en `.env`:

```
VITE_API_BASE_URL=http://localhost:8000
```

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

## Pendiente

- Sin CI.
- Sin tests de accesibilidad automatizados (la plantilla trae `vitest-axe` y
  `@axe-core/playwright` instalados, pero todavía sin usar).
- El desglose de factores no está traducido a gráfico; hoy es una lista.
- Sin notificación ni recordatorio a la hora de la ventana, que es la funcionalidad
  que haría que la app se use sin abrirla.
