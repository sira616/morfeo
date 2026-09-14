import { beforeEach, describe, expect, it } from 'vitest'
import { screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from './test-utils'
import { ProfilePage } from '@/pages/Profile'
import { server } from '@/mocks/server'
import { mockUser } from '@/mocks/fixtures'
import { useAuthStore } from '@/stores/authStore'

function login(overrides: Partial<typeof mockUser> = {}) {
  useAuthStore.getState().setSession({
    accessToken: 'mock-access',
    refreshToken: 'mock-refresh',
    user: { ...mockUser, ...overrides },
  })
}

/** Captura el cuerpo del PATCH /api/me para comprobar qué se manda de verdad. */
function capturarPatch() {
  const cuerpos: Record<string, unknown>[] = []
  server.use(
    http.patch('/api/me', async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>
      cuerpos.push(body)
      return HttpResponse.json({ ...mockUser, ...body })
    }),
  )
  return cuerpos
}

describe('Personalización del perfil', () => {
  beforeEach(() => login())

  it('el avatar cae a la inicial del nombre cuando no hay emoji', () => {
    login({ displayName: 'Sira', avatarEmoji: null })
    renderWithProviders(<ProfilePage />)
    // La cabecera de la tarjeta Identidad lleva el avatar con la inicial.
    expect(screen.getAllByText('S').length).toBeGreaterThan(0)
  })

  it('el emoji elegido manda sobre la inicial', () => {
    login({ displayName: 'Sira', avatarEmoji: '🦉' })
    renderWithProviders(<ProfilePage />)
    expect(screen.getAllByText('🦉').length).toBeGreaterThan(0)
  })

  it('marcar el horario de finde y quitarlo manda null, no lo omite', async () => {
    const user = userEvent.setup()
    login({ weekendWakeTime: '09:30:00' })
    const cuerpos = capturarPatch()
    renderWithProviders(<ProfilePage />)

    // Está marcado porque hay hora de finde; al desmarcar hay que mandar null para
    // borrarlo, no dejar de mandarlo (que lo dejaría igual).
    const casilla = screen.getByRole('checkbox', { name: /Me levanto a otra hora el finde/i })
    expect(casilla).toBeChecked()
    await user.click(casilla)

    const guardar = within(
      screen.getByText('Tus horarios').closest('div') as HTMLElement,
    ).getByRole('button', { name: /Guardar/i })
    await user.click(guardar)

    await waitFor(() => expect(cuerpos.length).toBeGreaterThan(0))
    expect(cuerpos[0]).toHaveProperty('weekend_wake_time', null)
  })

  it('elegir cronotipo búho lo manda en el patch', async () => {
    const user = userEvent.setup()
    const cuerpos = capturarPatch()
    renderWithProviders(<ProfilePage />)

    await user.click(screen.getByRole('button', { name: /Búho/i }))
    const guardar = within(
      screen.getByText('Sobre ti').closest('div') as HTMLElement,
    ).getByRole('button', { name: /Guardar/i })
    await user.click(guardar)

    await waitFor(() => expect(cuerpos.length).toBeGreaterThan(0))
    expect(cuerpos[0]).toHaveProperty('chronotype', 'buho')
  })
})
