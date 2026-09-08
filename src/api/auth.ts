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
}

export async function updateProfile(patch: ProfilePatch) {
  const user = await apiClient<AuthUser>('/api/me', { method: 'PATCH', body: patch })
  useAuthStore.getState().patchUser(user)
  return user
}
