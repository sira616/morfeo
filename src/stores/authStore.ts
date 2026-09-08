import { create } from 'zustand'

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
}

type AuthState = {
  accessToken: string | null
  refreshToken: string | null
  user: AuthUser | null
  setSession: (payload: {
    accessToken: string
    refreshToken: string
    user: AuthUser
  }) => void
  setTokens: (payload: { accessToken: string; refreshToken: string }) => void
  patchUser: (partial: Partial<AuthUser>) => void
  clearSession: () => void
}

/**
 * Los tokens viven solo en memoria, nunca en localStorage: aquí se guardan datos de
 * sueño y de estado de ánimo, y un token persistido es un token que sobrevive a
 * cerrar el navegador en un ordenador compartido.
 */
export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  setSession: ({ accessToken, refreshToken, user }) =>
    set({ accessToken, refreshToken, user }),
  setTokens: ({ accessToken, refreshToken }) =>
    set({ accessToken, refreshToken }),
  patchUser: (partial) =>
    set((state) => (state.user ? { user: { ...state.user, ...partial } } : {})),
  clearSession: () => set({ accessToken: null, refreshToken: null, user: null }),
}))
