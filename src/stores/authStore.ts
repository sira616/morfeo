import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

export type AuthUser = {
  id: string
  /** La identidad. El email es opcional y solo sirve para recuperar la contraseña. */
  username: string
  email: string | null
  emailVerified: boolean
  displayName: string
  onboardingDone: boolean
  isAdmin: boolean
  defaultWakeTime: string
  sleepNeedMinutes: number
  declaredLatencyMinutes: number
  wearableProvider: string | null
  // Personalización.
  weekendWakeTime: string | null
  avatarColor: string
  avatarEmoji: string | null
  goal: string | null
  chronotype: 'alondra' | 'intermedio' | 'buho'
  timezone: string
  poorEfficiencyThreshold: number
  /** Año de nacimiento, no la edad: no caduca cada cumpleaños. Null = no dado. */
  birthYear: number | null
}

type AuthState = {
  accessToken: string | null
  refreshToken: string | null
  user: AuthUser | null
  /** True mientras se intenta recuperar la sesión guardada al arrancar. */
  restoring: boolean
  setSession: (payload: {
    accessToken: string
    refreshToken: string
    user: AuthUser
  }) => void
  setTokens: (payload: { accessToken: string; refreshToken: string }) => void
  patchUser: (partial: Partial<AuthUser>) => void
  clearSession: () => void
  setRestored: () => void
}

/**
 * Igual que en `uiStore`: `localStorage` puede no estar (ventana privada,
 * almacenamiento bloqueado, un entorno de test que no lo expone). Sin respaldo, la app
 * revienta al arrancar en esos casos.
 */
function safeStorage(): Storage {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.getItem('__probe')
      return localStorage
    }
  } catch {
    // Almacenamiento bloqueado por el navegador: se cae al respaldo en memoria.
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

/**
 * Se guarda **solo el refresh token**, nunca el access ni el perfil.
 *
 * Antes no se guardaba nada y recargar la página cerraba la sesión, que en una app
 * añadida a la pantalla de inicio del móvil es insufrible: iOS la descarga de memoria
 * constantemente. El precio es que un refresh persistido sobrevive a cerrar el
 * navegador; se acota guardando el de menor valor posible —el access caduca en media
 * hora y no hace falta persistirlo—, rotándolo en cada uso y pudiendo revocarlo desde
 * el servidor, que es justo lo que un access sin estado no permite.
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      restoring: true,
      setSession: ({ accessToken, refreshToken, user }) =>
        set({ accessToken, refreshToken, user, restoring: false }),
      setTokens: ({ accessToken, refreshToken }) => set({ accessToken, refreshToken }),
      patchUser: (partial) =>
        set((state) => (state.user ? { user: { ...state.user, ...partial } } : {})),
      clearSession: () =>
        set({ accessToken: null, refreshToken: null, user: null, restoring: false }),
      setRestored: () => set({ restoring: false }),
    }),
    {
      name: 'mf-auth',
      version: 1,
      storage: createJSONStorage(safeStorage),
      partialize: (state) => ({ refreshToken: state.refreshToken }),
      // Sin token guardado no hay nada que restaurar, así que la app no debe quedarse
      // esperando: iría al login igual, pero con una pantalla en blanco por delante.
      onRehydrateStorage: () => (state) => {
        if (!state?.refreshToken) state?.setRestored()
      },
    },
  ),
)
