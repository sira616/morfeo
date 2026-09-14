import { apiClient } from '@/lib/apiClient'
import type { AuthUser } from '@/stores/authStore'
import { useAuthStore } from '@/stores/authStore'

type TokenPair = {
  access_token: string
  refresh_token: string
  user: AuthUser
}

function keep(data: TokenPair) {
  useAuthStore.getState().setSession({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    user: data.user,
  })
  return data.user
}

/** `login` acepta el usuario o el email: quien tiene los dos no debería recordar cuál puso. */
export async function login(loginName: string, password: string) {
  return keep(
    await apiClient<TokenPair>('/api/auth/login', {
      method: 'POST',
      body: { login: loginName, password },
      skipAuthRefresh: true,
    }),
  )
}

/** El email es opcional: la identidad es el nombre de usuario. */
export async function register(username: string, password: string, email?: string) {
  return keep(
    await apiClient<TokenPair>('/api/auth/register', {
      method: 'POST',
      body: { username, password, ...(email ? { email } : {}) },
      skipAuthRefresh: true,
    }),
  )
}

/**
 * Recupera la sesión guardada al arrancar.
 *
 * Solo se persiste el refresh, así que hay que canjearlo por un access y volver a
 * pedir el perfil. Si el token ya no vale —caducado, revocado, o la contraseña
 * cambió— se limpia y se acaba en el login, que es lo correcto.
 */
export async function restoreSession() {
  const { refreshToken, setRestored, clearSession } = useAuthStore.getState()
  if (!refreshToken) {
    setRestored()
    return
  }

  try {
    const tokens = await apiClient<{ access_token: string; refresh_token: string }>(
      '/api/auth/refresh',
      { method: 'POST', body: { refresh_token: refreshToken }, skipAuthRefresh: true },
    )
    useAuthStore.getState().setTokens({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
    })

    const user = await apiClient<AuthUser>('/api/me', { skipAuthRefresh: true })
    useAuthStore.getState().setSession({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      user,
    })
  } catch {
    clearSession()
  } finally {
    setRestored()
  }
}

export async function logout() {
  const refreshToken = useAuthStore.getState().refreshToken
  try {
    if (refreshToken) {
      await apiClient('/api/auth/logout', {
        method: 'POST',
        body: { refresh_token: refreshToken },
        skipAuthRefresh: true,
      })
    }
  } finally {
    useAuthStore.getState().clearSession()
  }
}

/**
 * Cambiar la contraseña cierra todas las sesiones, incluida esta: el backend revoca
 * los refresh, así que hay que volver a entrar. Es lo correcto —si alguien te la había
 * robado, seguiría dentro— y por eso la pantalla avisa antes.
 */
export async function changePassword(currentPassword: string, newPassword: string) {
  await apiClient<void>('/api/auth/change-password', {
    method: 'POST',
    body: { current_password: currentPassword, new_password: newPassword },
    skipAuthRefresh: true,
  })
}

export type VerificationStarted = {
  email: string
  /** False cuando el servidor no tiene SMTP: el código está en su consola. */
  sent_by_email: boolean
}

export async function startEmailVerification(email: string) {
  return apiClient<VerificationStarted>('/api/auth/email', { method: 'POST', body: { email } })
}

export async function verifyEmail(code: string) {
  await apiClient<void>('/api/auth/email/verify', { method: 'POST', body: { code } })
  useAuthStore.getState().patchUser({ emailVerified: true })
}

export type ProfilePatch = {
  display_name?: string
  default_wake_time?: string
  sleep_need_minutes?: number
  declared_latency_minutes?: number
  timezone?: string
  // `null` en estos tres es una orden de borrar (quitar el horario de finde, el emoji
  // o el objetivo); el backend los trata distinto del resto. Ver CLEARABLE en me.py.
  weekend_wake_time?: string | null
  avatar_emoji?: string | null
  goal?: string | null
  avatar_color?: string
  chronotype?: 'alondra' | 'intermedio' | 'buho'
  poor_efficiency_threshold?: number
}

export async function updateProfile(patch: ProfilePatch) {
  const user = await apiClient<AuthUser>('/api/me', { method: 'PATCH', body: patch })
  useAuthStore.getState().patchUser(user)
  return user
}
