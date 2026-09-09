import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

export type Theme = 'light' | 'dark' | 'noche'

/**
 * Franja en la que el modo noche profunda se enciende solo.
 *
 * Fija y no configurable a propósito: la alternativa era atarla a la ventana
 * recomendada de cada día, pero el tema tiene que funcionar también en el login,
 * donde todavía no hay usuario ni recomendación que consultar.
 */
export const NOCHE_START_HOUR = 22
export const NOCHE_END_HOUR = 6

export function isNightHour(now: Date = new Date()): boolean {
  const h = now.getHours()
  return h >= NOCHE_START_HOUR || h < NOCHE_END_HOUR
}

type UiState = {
  theme: Theme
  /** Si el modo noche se enciende solo al entrar en la franja nocturna. */
  autoNoche: boolean
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
  setAutoNoche: (on: boolean) => void
  /** Aplica la franja horaria. No hace nada si el automático está apagado. */
  syncNightTheme: (now?: Date) => void
}

const THEMES: Theme[] = ['light', 'dark', 'noche']

function applyThemeClass(theme: Theme) {
  const root = document.documentElement
  for (const name of THEMES) root.classList.toggle(name, name === theme)
  // `noche` es oscuro para el navegador: es lo que pinta las barras de scroll y los
  // controles nativos, y en claro sobre este fondo se ven como un recorte blanco.
  root.style.colorScheme = theme === 'light' ? 'light' : 'dark'
}

/**
 * `localStorage` no siempre está: ventana privada, almacenamiento bloqueado, o un
 * entorno de test que no lo expone. Sin este respaldo en memoria la app revienta al
 * arrancar en esos casos, y lo único que hay en juego es recordar el tema.
 */
function safeStorage(): Storage {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.getItem('__probe')
      return localStorage
    }
  } catch {
    // Almacenamiento bloqueado por el navegador: se cae al respaldo.
  }
  const memory = new Map<string, string>()
  return {
    getItem: (key) => memory.get(key) ?? null,
    setItem: (key, value) => void memory.set(key, value),
    removeItem: (key) => void memory.delete(key),
    clear: () => memory.clear(),
    key: (index) => [...memory.keys()][index] ?? null,
    get length() {
      return memory.size
    },
  }
}

export const useUiStore = create<UiState>()(
  persist(
    (set, get) => ({
      // Oscuro por defecto: la app se abre de noche, y un fogonazo blanco a las once
      // es justo lo contrario de lo que recomienda.
      theme: 'dark',
      autoNoche: true,
      setTheme: (theme) => {
        applyThemeClass(theme)
        // Elegir tema a mano apaga el automático. Si no, la app te lo cambiaría por
        // debajo al minuto siguiente y parecería que no le hace caso al botón.
        set({ theme, autoNoche: false })
      },
      toggleTheme: () => {
        const next = THEMES[(THEMES.indexOf(get().theme) + 1) % THEMES.length] as Theme
        applyThemeClass(next)
        set({ theme: next, autoNoche: false })
      },
      setAutoNoche: (on) => {
        set({ autoNoche: on })
        if (on) get().syncNightTheme()
      },
      syncNightTheme: (now = new Date()) => {
        const { autoNoche, theme } = get()
        if (!autoNoche) return
        // Al salir de la franja se vuelve a oscuro, no al tema que hubiera antes:
        // guardar "el de antes" significaba amanecer en claro por haber probado el
        // tema claro una vez a las tres de la tarde.
        const wanted: Theme = isNightHour(now) ? 'noche' : 'dark'
        if (wanted === theme) return
        applyThemeClass(wanted)
        set({ theme: wanted })
      },
    }),
    {
      name: 'mf-ui',
      version: 2,
      storage: createJSONStorage(safeStorage),
      onRehydrateStorage: () => (state) => {
        if (!state) return
        applyThemeClass(state.theme)
        // La franja se comprueba justo después de recuperar el tema guardado: abrir
        // la app a la una de la mañana tiene que entrar ya en noche, sin esperar al
        // primer tic del reloj.
        state.syncNightTheme()
      },
    },
  ),
)
