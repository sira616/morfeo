import { beforeEach, describe, expect, it } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './test-utils'
import { CheckinPage } from '@/pages/Checkin'
import { DevPage } from '@/pages/Dev'
import { RequireAdmin } from '@/router/RequireAdmin'
import { mockUser } from '@/mocks/fixtures'
import { useAuthStore } from '@/stores/authStore'

function login(overrides: Partial<typeof mockUser> = {}) {
  useAuthStore.getState().setSession({
    accessToken: 'mock-access',
    refreshToken: 'mock-refresh',
    user: { ...mockUser, ...overrides },
  })
}

describe('Check-in', () => {
  beforeEach(() => login())

  it('abre con el formulario, no con el chat', async () => {
    renderWithProviders(<CheckinPage />)
    // El chat necesita clave de LLM; el formulario funciona siempre, así que recibir
    // con una pestaña que puede no responder es una forma rara de empezar.
    expect(await screen.findByText('Guardar check-in')).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Rellenando' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
  })

  it('pregunta por el consumo del día, no solo por el ánimo', async () => {
    renderWithProviders(<CheckinPage />)
    expect(await screen.findByLabelText(/Cafés/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Unidades de alcohol/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Último porro/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Minutos de ejercicio/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Comidas del día/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Hora de la última/i)).toBeInTheDocument()
  })

  it('los días desde el último porro van en tramos, no en un número exacto', async () => {
    renderWithProviders(<CheckinPage />)
    const select = await screen.findByLabelText(/Último porro/i)
    expect(select.tagName).toBe('SELECT')
    expect(screen.getByRole('option', { name: 'Hace 2-3 días' })).toBeInTheDocument()
  })

  it('guarda y lo confirma', async () => {
    const user = userEvent.setup()
    renderWithProviders(<CheckinPage />)

    await user.click(await screen.findByRole('button', { name: 'Bien' }))
    await user.click(screen.getByRole('button', { name: 'Guardar check-in' }))

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent(/Guardado/i),
    )
  })

  it('se puede cambiar al chat', async () => {
    const user = userEvent.setup()
    renderWithProviders(<CheckinPage />)
    await user.click(screen.getByRole('tab', { name: 'Conversando' }))
    expect(await screen.findByText(/Qué tal ha ido el día/i)).toBeInTheDocument()
  })
})

describe('Panel de /dev', () => {
  it('lista los perfiles y su actividad', async () => {
    login({ isAdmin: true })
    renderWithProviders(<DevPage />)

    expect(await screen.findByText('demo@morfeo.app')).toBeInTheDocument()
    expect(screen.getByText('pablo@morfeo.app')).toBeInTheDocument()
    expect(screen.getByText(/nunca lo que escribió/i)).toBeInTheDocument()
  })

  it('a quien no es admin la guarda de interfaz lo saca de la ruta', async () => {
    login({ isAdmin: false })
    const { container } = renderWithProviders(
      <RequireAdmin />,
      { route: '/dev' },
    )
    // Redirige, así que no pinta nada del panel.
    expect(container).not.toHaveTextContent('demo@morfeo.app')
  })
})
