import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

export type Theme = 'light' | 'dark'

type UiState = {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
}

function applyThemeClass(theme: Theme) {
  const root = document.documentElement
  root.classList.toggle('dark', theme === 'dark')
  root.classList.toggle('light', theme === 'light')
  root.style.colorScheme = theme
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
      setTheme: (theme) => {
        applyThemeClass(theme)
        set({ theme })
      },
      toggleTheme: () => {
        const next = get().theme === 'light' ? 'dark' : 'light'
        applyThemeClass(next)
        set({ theme: next })
      },
    }),
    {
      name: 'mf-ui',
      version: 1,
      storage: createJSONStorage(safeStorage),
      onRehydrateStorage: () => (state) => {
        if (state) applyThemeClass(state.theme)
      },
    },
  ),
)
