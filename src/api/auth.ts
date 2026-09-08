import { apiClient } from '@/lib/apiClient'
import type { AuthUser } from '@/stores/authStore'
import { useAuthStore } from '@/stores/authStore'

type LoginResponse = {
  access_token: string
  refresh_token: string
  user: AuthUser
}

export async function login(email: string, password: string) {
  const data = await apiClient<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: { email, password },
    skipAuthRefresh: true,
  })
  useAuthStore.getState().setSession({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    user: data.user,
  })
  return data.user
}

export async function register(email: string, password: string) {
  await apiClient('/api/auth/register', {
    method: 'POST',
    body: { email, password },
    skipAuthRefresh: true,
  })
  return login(email, password)
}

export type ProfilePatch = {
  display_name?: string
  default_wake_time?: string
  sleep_need_minutes?: number
  declared_latency_minutes?: number
  timezone?: string
}

export async function updateProfile(patch: ProfilePatch) {
  const user = await apiClient<AuthUser>('/api/me', {
    method: 'PATCH',
    body: patch,
  })
  useAuthStore.getState().patchUser(user)
  return user
}

export async function logout() {
  try {
    await apiClient('/api/auth/logout', { method: 'POST', skipAuthRefresh: true })
  } finally {
    useAuthStore.getState().clearSession()
  }
}
