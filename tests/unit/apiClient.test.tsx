import { beforeEach, describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import { apiClient, ApiError } from '@/lib/apiClient'
import { useAuthStore } from '@/stores/authStore'
import { server } from '@/mocks/server'
import { __failNextRefresh } from '@/mocks/handlers'
import { mockUser } from '@/mocks/fixtures'

describe('apiClient: refresco de sesión', () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession()
  })

  it('ante un 401 refresca una vez y reintenta', async () => {
    useAuthStore.getState().setSession({
      accessToken: 'expired-token',
      refreshToken: 'refresh-ok',
      user: mockUser,
    })

    let hits = 0
    server.use(
      http.get('/api/sleep/nights', ({ request }) => {
        hits += 1
        if (request.headers.get('Authorization') === 'Bearer expired-token') {
          return HttpResponse.json({ detail: 'expired' }, { status: 401 })
        }
        return HttpResponse.json([])
      }),
    )

    const nights = await apiClient<unknown[]>('/api/sleep/nights')
    expect(nights).toEqual([])
    expect(hits).toBeGreaterThanOrEqual(2)
    expect(useAuthStore.getState().accessToken).not.toBe('expired-token')
  })

  it('si el refresco falla, cierra la sesión en vez de reintentar en bucle', async () => {
    useAuthStore.getState().setSession({
      accessToken: 'expired',
      refreshToken: 'bad',
      user: mockUser,
    })
    __failNextRefresh()

    server.use(
      http.get('/api/me', () => HttpResponse.json({ detail: 'expired' }, { status: 401 })),
    )

    await expect(apiClient('/api/me')).rejects.toBeInstanceOf(ApiError)
    expect(useAuthStore.getState().accessToken).toBeNull()
  })
})
