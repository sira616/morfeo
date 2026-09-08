import { beforeEach, describe, expect, it } from 'vitest'
import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './test-utils'
import { TonightPage } from '@/pages/Tonight'
import { NightLogForm } from '@/components/night/NightLogForm'
import { mockUser } from '@/mocks/fixtures'
import { useAuthStore } from '@/stores/authStore'

function login() {
  useAuthStore.getState().setSession({
    accessToken: 'mock-access',
    refreshToken: 'mock-refresh',
    user: mockUser,
  })
}

describe('Página «Esta noche»', () => {
  beforeEach(login)

  it('muestra la ventana y separa acostarse de dormirse', async () => {
    renderWithProviders(<TonightPage />)

    expect(await screen.findByText('23:15 – 23:55')).toBeInTheDocument()
    expect(screen.getByText(/No es la hora de dormirte/i)).toBeInTheDocument()
  })

  it('el arco describe la noche para quien no lo ve', async () => {
    renderWithProviders(<TonightPage />)
    const arco = await screen.findByRole('img', { name: /Te acuestas a las 23:35/i })
    expect(arco).toHaveAccessibleName(/tardas 30 minutos en dormirte/i)
  })

  it('el desglose no ocupa la portada: vive detrás de una pregunta', async () => {
    const user = userEvent.setup()
    renderWithProviders(<TonightPage />)

    // Cerrado, el <dialog> no está en el árbol accesible: competía con la única cifra
    // que importa.
    expect(await screen.findByRole('button', { name: /Por qué esta hora/i })).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Por qué esta hora/i }))

    const dialogo = await screen.findByRole('dialog')
    expect(within(dialogo).getByText('Necesidad basal')).toBeInTheDocument()
    expect(within(dialogo).getByText('Deuda de sueño')).toBeInTheDocument()
    expect(within(dialogo).getByText('+60 min')).toBeInTheDocument()
    expect(within(dialogo).getByText(/Confianza alta/i)).toBeInTheDocument()
  })

  it('avisa cuando la ventana viene comprimida a propósito', async () => {
    renderWithProviders(<TonightPage />)
    expect(await screen.findByText(/Ventana comprimida a propósito/i)).toBeInTheDocument()
  })

  it('resume el histórico donde antes estaba el desglose', async () => {
    renderWithProviders(<TonightPage />)

    expect(await screen.findByText('Tu histórico')).toBeInTheDocument()
    expect(screen.getByText('Sueño medio')).toBeInTheDocument()
    expect(await screen.findByText('A qué hora te acostaste')).toBeInTheDocument()
    expect(await screen.findByText('Cómo has estado')).toBeInTheDocument()
  })

  it('los consejos enseñan su nivel de evidencia', async () => {
    renderWithProviders(<TonightPage />)
    expect(await screen.findByText('Cinco cosas que ayudan')).toBeInTheDocument()
    expect((await screen.findAllByText('Evidencia alta')).length).toBeGreaterThan(0)
    expect(screen.getByText(/Hábitos, no tratamiento/i)).toBeInTheDocument()
  })
})

describe('Registro de la noche', () => {
  beforeEach(login)

  it('no pregunta cuántos minutos dormiste: lo calcula', async () => {
    renderWithProviders(<NightLogForm />)

    // De 23:30 a 07:00 son 7 h 30; menos 20 min de conciliación, 7 h 10 de sueño.
    const resumen = await screen.findByRole('status')
    expect(resumen).toHaveTextContent('7 h 10')
    expect(resumen).toHaveTextContent('7 h 30 en la cama')
  })

  it('rehace la cuenta al cambiar la latencia', async () => {
    const user = userEvent.setup()
    renderWithProviders(<NightLogForm />)

    const latencia = screen.getByLabelText(/Cuánto tardaste en dormirte/i)
    await user.clear(latencia)
    await user.type(latencia, '90')

    expect(await screen.findByRole('status')).toHaveTextContent('6 h 00')
  })

  it('cruza medianoche sin romperse', async () => {
    const user = userEvent.setup()
    renderWithProviders(<NightLogForm />)

    const acostarse = screen.getByLabelText(/A qué hora te acostaste/i)
    await user.clear(acostarse)
    await user.type(acostarse, '01:00')

    // De 01:00 a 07:00 son 6 h, no menos veintitantas.
    expect(await screen.findByRole('status')).toHaveTextContent('6 h 00 en la cama')
  })

  it('avisa en vez de dejar guardar una noche imposible', async () => {
    const user = userEvent.setup()
    renderWithProviders(<NightLogForm />)

    const despierta = screen.getByLabelText(/Cuánto estuviste despierta/i)
    await user.clear(despierta)
    await user.type(despierta, '600')

    expect(await screen.findByRole('status')).toHaveTextContent(/no queda tiempo dormido/i)
    expect(screen.getByRole('button', { name: /Guardar la noche/i })).toBeDisabled()
  })
})
