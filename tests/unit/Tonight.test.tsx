import { beforeEach, describe, expect, it } from 'vitest'
import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './test-utils'
import { TonightPage } from '@/pages/Tonight'
import { NightLogForm } from '@/components/night/NightLogForm'
import { http, HttpResponse } from 'msw'
import { server } from '@/mocks/server'
import { mockRecommendation, mockUser } from '@/mocks/fixtures'
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

describe('Coordinación de la hora de despertar', () => {
  beforeEach(login)

  it('el tiempo en la cama incluye la conciliación', async () => {
    renderWithProviders(<TonightPage />)
    // 6 h 55 de ventana de sueño + 30 min conciliando = 7 h 25 en la cama. Antes se
    // enseñaba la ventana pelada y no cuadraba con el arco de arriba.
    expect((await screen.findAllByText(/7 h 25 min en la cama/)).length).toBeGreaterThan(0)
    expect(screen.queryByText(/6 h 55 min en la cama/)).not.toBeInTheDocument()
  })

  it('no dice de dónde viene la hora cuando sale del perfil', async () => {
    renderWithProviders(<TonightPage />)
    await screen.findByText('23:15 – 23:55')
    expect(screen.queryByText(/viene del check-in/i)).not.toBeInTheDocument()
  })

  it('cuando manda el check-in lo dice y deja volver al perfil', async () => {
    server.use(
      http.get('/api/bedtime/tonight', () =>
        HttpResponse.json({ ...mockRecommendation, wake_target_source: 'checkin' }),
      ),
    )
    renderWithProviders(<TonightPage />)

    // Sin este aviso, cambiar la hora en el perfil no hacía nada visible.
    expect(await screen.findByText(/viene del check-in de hoy/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Usar la de mi perfil/i })).toBeInTheDocument()
  })
})

describe('Simulador', () => {
  beforeEach(login)

  it('«Hoy» y «Ninguno» son cosas distintas, y solo la segunda se manda', async () => {
    const user = userEvent.setup()
    const urls: string[] = []
    server.use(
      http.get('/api/bedtime/tonight', ({ request }) => {
        urls.push(request.url)
        return HttpResponse.json(mockRecommendation)
      }),
    )

    renderWithProviders(<TonightPage />)
    await screen.findByText('23:15 – 23:55')

    // El estado inicial no manda nada: pedir la del día es lo que la guarda, y una
    // simulación no debe guardarse nunca.
    expect(urls.every((url) => !url.includes('coffees'))).toBe(true)

    await user.click(screen.getByRole('button', { name: 'Ninguno' }))
    await screen.findByText(/Simulación/i)

    // «Ninguno» viaja como coffees=0, no como campo ausente: sin esa diferencia no se
    // puede preguntar qué pasaría en un día sin café.
    expect(urls.some((url) => url.includes('coffees=0'))).toBe(true)
  })

  it('dice cuánto se mueve la hora, no solo cuál sería', async () => {
    const user = userEvent.setup()
    renderWithProviders(<TonightPage />)
    await screen.findByText('23:15 – 23:55')

    await user.click(screen.getByRole('button', { name: '1 h' }))

    // El mock adelanta media hora por una siesta de 60 min. Lo que importa del texto
    // es que compare con la hora real, no que enseñe una hora suelta.
    const aviso = (await screen.findByText(/Simulación/i)).closest('p')!
    expect(aviso).toHaveTextContent('30 min más tarde')
    expect(aviso).toHaveTextContent('23:35')
  })

  it('mientras simulas no se puede marcar la recomendación como seguida', async () => {
    const user = userEvent.setup()
    renderWithProviders(<TonightPage />)
    await screen.findByText('23:15 – 23:55')
    expect(screen.getByRole('button', { name: 'La seguí' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Ninguno' }))

    // Marcar «la seguí» sobre una hora inventada ensuciaría justo el dato con el que
    // se comprueba si el motor acierta.
    expect(screen.queryByRole('button', { name: 'La seguí' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Volver a mi día real/i }))
    expect(await screen.findByRole('button', { name: 'La seguí' })).toBeInTheDocument()
  })

  it('la hora del café solo se pregunta cuando hay café', async () => {
    const user = userEvent.setup()
    renderWithProviders(<TonightPage />)
    await screen.findByText('23:15 – 23:55')

    expect(screen.queryByLabelText(/El último, a las/i)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '2' }))
    expect(await screen.findByLabelText(/El último, a las/i)).toBeInTheDocument()
  })
})
