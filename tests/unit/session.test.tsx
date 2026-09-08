import { beforeEach, describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import { restoreSession } from '@/api/auth'
import { server } from '@/mocks/server'
import { useAuthStore } from '@/stores/authStore'

describe('Recuperar la sesión al recargar', () => {
  beforeEach(() => {
    useAuthStore.getState().clearSession()
  })

  it('canjea el refresh guardado y recupera el perfil', async () => {
    // Lo que queda tras un F5: el refresh persistido y nada más.
    useAuthStore.setState({ refreshToken: 'mock-refresh', accessToken: null, user: null })

    await restoreSession()

    const state = useAuthStore.getState()
    expect(state.accessToken).toBe('mock-access-2')
    expect(state.user?.username).toBeTruthy()
    expect(state.restoring).toBe(false)
  })

  it('sin token guardado no se queda esperando', async () => {
    useAuthStore.setState({ refreshToken: null, restoring: true })

    await restoreSession()

    // Si `restoring` se quedara en true, la app enseñaría una pantalla en blanco en
    // vez de mandar al login.
    expect(useAuthStore.getState().restoring).toBe(false)
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('si el refresh ya no vale, limpia y no deja la sesión a medias', async () => {
    server.use(
      http.post('/api/auth/refresh', () =>
        HttpResponse.json({ detail: 'Sesión caducada' }, { status: 401 }),
      ),
    )
    useAuthStore.setState({ refreshToken: 'caducado', accessToken: null, user: null })

    await restoreSession()

    const state = useAuthStore.getState()
    expect(state.refreshToken).toBeNull()
    expect(state.accessToken).toBeNull()
    expect(state.restoring).toBe(false)
  })

  it('solo persiste el refresh, nunca el access ni el perfil', () => {
    // El access caduca en media hora y no hace falta guardarlo; el perfil se vuelve a
    // pedir. Cuanto menos haya en el disco, menos hay que robar. Se comprueba sobre
    // `partialize` y no leyendo localStorage, que en este entorno no existe.
    const partialize = useAuthStore.persist.getOptions().partialize
    const guardado = partialize?.(useAuthStore.getState()) ?? {}
    expect(Object.keys(guardado)).toEqual(['refreshToken'])
  })
})
