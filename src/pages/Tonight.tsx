import { useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { AlertTriangle, Info } from 'lucide-react'
import { Button } from '@/components/atoms/Button'
import { Modal } from '@/components/atoms/Modal'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { NightArc } from '@/components/night/NightArc'
import { SleepSummaryCard } from '@/components/night/SleepSummaryCard'
import { Simulator } from '@/components/night/Simulator'
import { TipsCard } from '@/components/night/TipsCard'
import {
  clearCheckinWakeTarget,
  getTonight,
  isSimulating,
  markFollowed,
  type Recommendation,
  type SimulationParams,
} from '@/api/morfeo'
import { routes } from '@/router/paths'

function hhmm(value: string): string {
  return value.slice(0, 5)
}

function duration(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  // Sin el primer caso salía «0 h 20 min». No se veía hasta que el simulador empezó a
  // enseñar diferencias de menos de una hora, que son casi todas.
  if (h === 0) return `${m} min`
  return m === 0 ? `${h} h` : `${h} h ${m} min`
}

/**
 * Minutos entre dos horas, con signo y por el camino corto.
 *
 * Sin lo del camino corto, comparar las 23:50 con las 00:10 daba 1420 min de
 * diferencia en vez de 20: el simulador diría que te acuestas casi un día antes cada
 * vez que la hora cruza la medianoche, que es la mitad de las noches.
 */
function minutesBetween(from: string, to: string): number {
  const parse = (v: string) => {
    const [h, m] = v.split(':').map(Number)
    return (h ?? 0) * 60 + (m ?? 0)
  }
  const diff = ((parse(to) - parse(from) + 1440) % 1440 + 1440) % 1440
  return diff > 720 ? diff - 1440 : diff
}

const CONFIDENCE_COPY: Record<Recommendation['confidence'], string> = {
  baja: 'Con pocas noches medidas todavía. Se afina sola conforme apuntes noches.',
  media: 'Basada en unos días de datos.',
  alta: 'Basada en dos semanas o más de noches medidas.',
}

/** Suma minutos a un "HH:MM:SS" y devuelve "HH:MM", cruzando medianoche. */
function addMinutes(time: string, minutes: number): string {
  const [h, m] = time.split(':').map(Number)
  const total = ((h ?? 0) * 60 + (m ?? 0) + minutes + 1440) % 1440
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}

/**
 * La portada dice una cosa: a qué hora meterte en la cama.
 *
 * El desglose de factores vive en una ventana que se abre desde el propio widget, no
 * en una tarjeta aparte. Es información que se consulta cuando te preguntas "¿y esto
 * por qué?", no cada vez que abres la app, y tenerla siempre desplegada competía con
 * la única cifra que importa.
 */
export function TonightPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [sim, setSim] = useState<SimulationParams>({})
  const [whyOpen, setWhyOpen] = useState(false)
  const simulando = isSimulating(sim)

  // La real se pide siempre, incluso mientras simulas: es la que el servidor congela
  // como recomendación del día, y es contra la que se compara la simulada. Sin ella
  // el simulador enseñaría una hora suelta, que no dice nada.
  const real = useQuery({ queryKey: ['tonight'], queryFn: () => getTonight() })
  const simulada = useQuery({
    queryKey: ['tonight', sim],
    queryFn: () => getTonight(sim),
    enabled: simulando,
    // Mantener la respuesta anterior mientras llega la nueva: si no, cada ficha que
    // tocas apaga la cifra medio segundo y el efecto de «se mueve» se pierde.
    placeholderData: keepPreviousData,
  })

  const { isLoading, isError } = real
  const data = (simulando ? simulada.data : undefined) ?? real.data

  const follow = useMutation({
    mutationFn: (followed: boolean) => markFollowed(data!.day, followed),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tonight'] })
      // Marcarlo solo dice si te acostaste a la hora; lo que cierra el bucle es qué
      // pasó después, así que se encadena con el registro de la noche.
      navigate(routes.night)
    },
  })

  if (isLoading) return <p className="py-8 text-center opacity-70">Calculando…</p>
  if (isError || !data) {
    return (
      <p className="py-8 text-center opacity-70">
        No se pudo calcular la recomendación. Reintenta en un momento.
      </p>
    )
  }

  return (
    <div className="grid items-start gap-6 lg:grid-cols-2 lg:gap-8">
      {/* --- Columna izquierda: la noche --- */}
      <div className="flex flex-col gap-6">
        <SurfaceCard className="text-center">
          <p className="text-body-sm opacity-70">A la cama entre</p>
          <p className="text-display-md font-bold tabular-nums">
            {hhmm(data.window_start)} – {hhmm(data.window_end)}
          </p>
          <p className="mt-1 text-body-sm opacity-80">
            No es la hora de dormirte: entre una cosa y otra hay{' '}
            {data.onset_latency_minutes} min de conciliación.
          </p>

          <div className="mt-4">
            <NightArc recommendation={data} />
          </div>

          {/* `time_in_bed_minutes` suma la conciliación; `sleep_window_minutes` no.
              Enseñar el segundo como "en la cama" era la razón de que este texto no
              cuadrara con el arco de arriba. */}
          <p className="mt-3 text-body-sm opacity-70">
            {data.sleep_window_minutes < data.target_sleep_minutes ? null : (
              <>Objetivo: {duration(data.target_sleep_minutes)} de sueño · </>
            )}
            {duration(data.time_in_bed_minutes)} en la cama · despertar a{' '}
            {hhmm(data.wake_target)}
          </p>

          {simulando && real.data ? (
            <SimulationDelta real={real.data} simulada={data} />
          ) : (
            <WakeSource recommendation={data} />
          )}

          <button
            type="button"
            onClick={() => setWhyOpen(true)}
            className="mt-3 min-h-touch text-body-sm underline opacity-80 hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo"
          >
            ¿Por qué esta hora?
          </button>
        </SurfaceCard>

        {data.mode === 'restriccion' ? (
          <SurfaceCard>
            <p className="flex items-start gap-2 text-body-sm">
              <AlertTriangle
                aria-hidden
                size={18}
                className="mt-0.5 shrink-0"
                style={{ color: 'var(--mf-chart-awake)' }}
              />
              <span>
                <strong>Ventana comprimida a propósito.</strong> Puede parecer poco tiempo,
                y es intencionado: mira el porqué antes de ampliarla por tu cuenta.
              </span>
            </p>
          </SurfaceCard>
        ) : null}

        <Simulator sim={sim} onChange={setSim} activo={simulando} />

        {!simulando ? (
          <SurfaceCard>
            <p className="mb-2 text-body-sm font-semibold">¿Seguiste la recomendación de ayer?</p>
            <div className="flex gap-2">
              <Button
                fullWidth
                variant={data.followed === true ? 'primary' : 'secondary'}
                onClick={() => follow.mutate(true)}
              >
                La seguí
              </Button>
              <Button
                fullWidth
                variant={data.followed === false ? 'primary' : 'ghost'}
                onClick={() => follow.mutate(false)}
              >
                No la seguí
              </Button>
            </div>
            <p className="mt-2 text-body-sm opacity-60">
              Después te pregunto cómo fue la noche: eso es lo que hace que la hora se
              ajuste a ti.
            </p>
          </SurfaceCard>
        ) : null}
      </div>

      {/* --- Columna derecha: cómo vas y qué ayuda --- */}
      <div className="flex flex-col gap-6">
        <SleepSummaryCard />
        <TipsCard />
        <Link to={routes.checkin} className="text-center text-body-sm underline">
          Contarle cómo ha ido el día
        </Link>
      </div>

      <WhyModal open={whyOpen} onClose={() => setWhyOpen(false)} recommendation={data} />
    </div>
  )
}

/**
 * Lo que convierte el simulador en algo que se entiende: no la hora simulada, sino
 * cuánto se ha movido respecto a la de verdad. Una hora suelta no dice nada; «40 min
 * antes» sí.
 */
function SimulationDelta({
  real,
  simulada,
}: {
  real: Recommendation
  simulada: Recommendation
}) {
  const diferencia = minutesBetween(real.bedtime, simulada.bedtime)
  const absoluta = Math.abs(diferencia)

  return (
    <p
      className="mt-2 rounded-md px-3 py-2 text-body-sm"
      style={{ background: 'var(--mf-tint-indigo)' }}
    >
      <strong>Simulación.</strong>{' '}
      {absoluta === 0 ? (
        <>Con esos cambios la hora no se movería.</>
      ) : (
        <>
          {duration(absoluta)} {diferencia > 0 ? 'más tarde' : 'antes'} que tu hora real,
          que son las {hhmm(real.bedtime)}.
        </>
      )}
    </p>
  )
}

/**
 * De dónde sale la hora de despertar.
 *
 * El check-in de hoy manda sobre el perfil, y eso está bien: "mañana me levanto a las
 * seis" es más específico que un valor por defecto. Lo que estaba mal era no decirlo,
 * porque cambiar la hora en el perfil no hacía nada visible y parecía un cuelgue.
 */
function WakeSource({ recommendation }: { recommendation: Recommendation }) {
  const queryClient = useQueryClient()
  const clear = useMutation({
    mutationFn: clearCheckinWakeTarget,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tonight'] }),
  })

  if (recommendation.wake_target_source !== 'checkin') return null

  return (
    <p className="mt-2 text-body-sm opacity-70">
      Esa hora viene del check-in de hoy, no de tu perfil.{' '}
      <button
        type="button"
        onClick={() => clear.mutate()}
        disabled={clear.isPending}
        className="underline hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo"
      >
        Usar la de mi perfil
      </button>
    </p>
  )
}

function WhyModal({
  open,
  onClose,
  recommendation,
}: {
  open: boolean
  onClose: () => void
  recommendation: Recommendation
}) {
  const asleepAt = addMinutes(recommendation.bedtime, recommendation.onset_latency_minutes)

  return (
    <Modal open={open} onClose={onClose} title="Por qué esta hora">
      <p className="mb-4 text-body-sm opacity-80">
        Para levantarte a las {hhmm(recommendation.wake_target)} necesitas{' '}
        {duration(recommendation.time_in_bed_minutes)} en la cama, y{' '}
        {recommendation.onset_latency_minutes} min más para dormirte. De ahí sale
        acostarte a las {hhmm(recommendation.bedtime)} y dormir sobre las {asleepAt}.
      </p>

      <ul className="flex flex-col gap-2">
        {recommendation.factors.map((factor) => (
          <li key={factor.label} className="flex items-baseline justify-between gap-3">
            <span>
              <strong>{factor.label}</strong>
              <span className="block text-body-sm opacity-70">{factor.detail}</span>
            </span>
            <span
              className="shrink-0 tabular-nums"
              style={{ color: factor.minutes < 0 ? 'var(--mf-good)' : undefined }}
            >
              {factor.minutes > 0 ? '+' : ''}
              {factor.minutes} min
            </span>
          </li>
        ))}
      </ul>

      {recommendation.notes.length > 0 ? (
        <ul
          className="mt-3 flex flex-col gap-2 border-t pt-3"
          style={{ borderColor: 'var(--mf-line)' }}
        >
          {recommendation.notes.map((note) => (
            <li key={note} className="flex items-start gap-2 text-body-sm">
              <Info aria-hidden size={16} className="mt-0.5 shrink-0" />
              {note}
            </li>
          ))}
        </ul>
      ) : null}

      <p className="mt-4 text-body-sm opacity-70">
        Confianza {recommendation.confidence}. {CONFIDENCE_COPY[recommendation.confidence]}
      </p>
    </Modal>
  )
}
