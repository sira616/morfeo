import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { getNights, getRecentCheckins, type Night, type RecentCheckin } from '@/api/morfeo'
import { routes } from '@/router/paths'

const WINDOW_DAYS = 14

const MOOD_LABELS = ['', 'fatal', 'regular', 'normal', 'bien', 'genial']

function duration(minutes: number): string {
  return `${Math.floor(minutes / 60)} h ${String(Math.round(minutes % 60)).padStart(2, '0')}`
}

function hhmm(iso: string): string {
  return iso.slice(11, 16)
}

function dayLabel(iso: string): string {
  const [, m, d] = iso.split('-')
  return `${d}/${m}`
}

function moodColor(mood: number): string {
  if (mood >= 4) return 'var(--mf-good)'
  if (mood === 3) return 'var(--mf-chart-in-bed)'
  return 'var(--mf-chart-awake)'
}

/**
 * Resumen del histórico en la portada.
 *
 * Ocupa el sitio donde estaba el desglose de factores, que se ha ido a una ventana
 * dentro del propio widget de la hora. La diferencia es de propósito: el desglose
 * explica *esta* noche y solo interesa cuando te lo preguntas, mientras que esto
 * contesta "¿cómo voy?", que es lo que uno mira todos los días.
 */
export function SleepSummaryCard() {
  const { data: nights = [], isLoading } = useQuery({
    queryKey: ['nights', WINDOW_DAYS],
    queryFn: () => getNights(WINDOW_DAYS),
  })
  const { data: checkins = [] } = useQuery({
    queryKey: ['recent-checkins'],
    queryFn: () => getRecentCheckins(WINDOW_DAYS),
  })

  if (isLoading) {
    return (
      <SurfaceCard>
        <p className="text-body-sm opacity-70">Cargando el resumen…</p>
      </SurfaceCard>
    )
  }

  if (nights.length === 0) {
    return (
      <SurfaceCard>
        <h2 className="text-headline-sm font-bold">Tu histórico</h2>
        <p className="mt-2 text-body-sm opacity-70">
          Todavía no hay noches. Apunta la de ayer y la recomendación empieza a ajustarse
          a ti en vez de a una media.
        </p>
        <Link to={routes.night} className="mt-3 inline-block text-body-sm underline">
          Contar cómo fue anoche
        </Link>
      </SurfaceCard>
    )
  }

  return (
    <SurfaceCard>
      <h2 className="text-headline-sm font-bold">Tu histórico</h2>
      <p className="mb-4 text-body-sm opacity-70">Últimas {nights.length} noches.</p>

      <Averages nights={nights} />
      <RecentBedtimes nights={nights} />
      <Moods checkins={checkins} />

      <Link to={routes.history} className="mt-4 inline-block text-body-sm underline">
        Ver el historial completo
      </Link>
    </SurfaceCard>
  )
}

function Averages({ nights }: { nights: Night[] }) {
  const sleep = nights.reduce((sum, n) => sum + n.total_sleep_minutes, 0) / nights.length
  const efficiency = nights.reduce((sum, n) => sum + n.efficiency, 0) / nights.length
  const measured = nights.filter((n) => n.onset_latency_minutes !== null)
  const latency = measured.length
    ? measured.reduce((sum, n) => sum + (n.onset_latency_minutes ?? 0), 0) / measured.length
    : null

  return (
    <dl className="grid grid-cols-3 gap-3 text-body-sm">
      <div>
        <dt className="opacity-60">Sueño medio</dt>
        <dd className="text-headline-sm font-bold tabular-nums">{duration(sleep)}</dd>
      </div>
      <div>
        <dt className="opacity-60">Eficiencia</dt>
        <dd
          className="text-headline-sm font-bold tabular-nums"
          style={{ color: efficiency >= 0.85 ? 'var(--mf-good)' : undefined }}
        >
          {Math.round(efficiency * 100)}%
        </dd>
      </div>
      <div>
        <dt className="opacity-60">Tardas</dt>
        <dd className="text-headline-sm font-bold tabular-nums">
          {latency === null ? '—' : `${Math.round(latency)} min`}
        </dd>
      </div>
    </dl>
  )
}

function RecentBedtimes({ nights }: { nights: Night[] }) {
  // Solo las noches con hora real: sin `bed_at` no hay nada que enseñar, y rellenar
  // el hueco con la hora recomendada sería inventar.
  const withTime = nights.filter((n) => n.bed_at).slice(-5).reverse()
  if (withTime.length === 0) return null

  return (
    <div className="mt-4 border-t pt-3" style={{ borderColor: 'var(--mf-line)' }}>
      <h3 className="mb-2 text-body-sm font-bold">A qué hora te acostaste</h3>
      <ul className="flex flex-col gap-1 text-body-sm">
        {withTime.map((night) => (
          <li key={night.night_of} className="flex justify-between gap-3">
            <span className="opacity-70">{dayLabel(night.night_of)}</span>
            <span className="tabular-nums">{hhmm(night.bed_at as string)}</span>
            <span className="tabular-nums opacity-70">
              {duration(night.total_sleep_minutes)} dormidas
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Moods({ checkins }: { checkins: RecentCheckin[] }) {
  const withMood = checkins.filter((c) => c.mood !== null).slice(-10)
  if (withMood.length === 0) return null

  const last = withMood[withMood.length - 1]!

  return (
    <div className="mt-4 border-t pt-3" style={{ borderColor: 'var(--mf-line)' }}>
      <h3 className="mb-2 text-body-sm font-bold">Cómo has estado</h3>
      <div className="flex flex-wrap items-center gap-1.5">
        {withMood.map((checkin) => (
          <span
            key={checkin.day}
            className="h-4 w-4 rounded-full"
            style={{ background: moodColor(checkin.mood as number) }}
            title={`${dayLabel(checkin.day)}: ${MOOD_LABELS[checkin.mood as number]}`}
          />
        ))}
        <span className="ml-1 text-body-sm opacity-70">
          hoy, {MOOD_LABELS[last.mood as number]}
        </span>
      </div>
    </div>
  )
}
