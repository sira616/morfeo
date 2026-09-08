import { beforeEach, describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from './test-utils'
import { TonightPage } from '@/pages/Tonight'
import { mockUser } from '@/mocks/fixtures'
import { useAuthStore } from '@/stores/authStore'

describe('Página «Esta noche»', () => {
  beforeEach(() => {
    useAuthStore.getState().setSession({
      accessToken: 'mock-access',
      refreshToken: 'mock-refresh',
      user: mockUser,
    })
  })

  it('muestra la ventana y separa acostarse de dormirse', async () => {
    renderWithProviders(<TonightPage />)

    expect(await screen.findByText('23:15 – 23:55')).toBeInTheDocument()

    // El mensaje que justifica la app entera: la hora es de meterse en la cama, y los
    // 30 min de conciliación llevan el sueño real a las 00:05.
    expect(screen.getByText(/No es la hora de dormirte/i)).toBeInTheDocument()
    expect(screen.getByText('00:05')).toBeInTheDocument()
  })

  it('desglosa los factores en vez de dar la hora a secas', async () => {
    renderWithProviders(<TonightPage />)

    expect(await screen.findByText('Necesidad basal')).toBeInTheDocument()
    expect(screen.getByText('Deuda de sueño')).toBeInTheDocument()
    expect(screen.getByText('+60 min')).toBeInTheDocument()
  })

  it('avisa cuando la ventana viene comprimida a propósito', async () => {
    renderWithProviders(<TonightPage />)

    expect(await screen.findByText(/Ventana comprimida a propósito/i)).toBeInTheDocument()
  })
})

describe('Arco de la noche y consejos', () => {
  beforeEach(() => {
    useAuthStore.getState().setSession({
      accessToken: 'mock-access',
      refreshToken: 'mock-refresh',
      user: mockUser,
    })
  })

  it('el arco describe la noche para quien no lo ve', async () => {
    renderWithProviders(<TonightPage />)
    const arco = await screen.findByRole('img', { name: /Te acuestas a las 23:35/i })
    expect(arco).toBeInTheDocument()
    expect(arco).toHaveAccessibleName(/tardas 30 minutos en dormirte/i)
  })

  it('los consejos enseñan su nivel de evidencia', async () => {
    renderWithProviders(<TonightPage />)
    expect(await screen.findByText('Cinco cosas que ayudan')).toBeInTheDocument()
    // La decisión de producto que separa esto de una lista de tópicos. Se espera al
    // fetch: la cabecera se pinta antes de que lleguen los consejos.
    expect((await screen.findAllByText('Evidencia alta')).length).toBeGreaterThan(0)
    expect(screen.getByText(/no curan el insomnio|no son un tratamiento|Hábitos, no tratamiento/i)).toBeInTheDocument()
  })
})
