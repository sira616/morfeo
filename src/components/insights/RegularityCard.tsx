import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import type { Regularity, SocialJetlag } from '@/api/morfeo'

function clock(minutesFromMidnight: number): string {
  const h = Math.floor(minutesFromMidnight / 60) % 24
  const m = minutesFromMidnight % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

function scoreColor(score: number): string {
  if (score >= 70) return 'var(--mf-good)'
  if (score >= 40) return 'var(--mf-chart-awake)'
  return 'var(--mf-error)'
}

export function RegularityCard({
  regularity,
  jetlag,
}: {
  regularity: Regularity | null
  jetlag: SocialJetlag | null
}) {
  // Sin horas reales no hay fase que medir. Se dice, en vez de pintar un cero que se
  // leería como "tienes un horario malísimo".
  if (!regularity) {
    return (
      <SurfaceCard>
        <h2 className="text-headline-sm font-bold">Regularidad</h2>
        <p className="mt-2 text-body-sm opacity-70">
          Hacen falta al menos cinco noches con hora de dormirse y de despertar. Muchos
          importadores solo traen la duración; si el tuyo las trae, aparecerá aquí sola.
        </p>
      </SurfaceCard>
    )
  }

  return (
    <SurfaceCard>
      <h2 className="text-headline-sm font-bold">Regularidad</h2>
      <p className="mb-3 text-body-sm opacity-70">
        Cuánto se parece una noche a otra, sobre {regularity.nights} noches.
      </p>

      <div className="flex items-baseline gap-2">
        <span
          className="text-display-md font-bold tabular-nums"
          style={{ color: scoreColor(regularity.score) }}
        >
          {regularity.score}
        </span>
        <span className="text-body-sm opacity-60">/ 100</span>
      </div>

      <div
        className="mt-2 h-2 w-full overflow-hidden rounded-full"
        style={{ background: 'var(--mf-line)' }}
        role="img"
        aria-label={`Puntuación de regularidad: ${regularity.score} sobre 100`}
      >
        <div
          className="h-full rounded-full"
          style={{ width: `${regularity.score}%`, background: scoreColor(regularity.score) }}
        />
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-body-sm">
        <div>
          <dt className="opacity-60">Punto medio del sueño</dt>
          <dd className="font-bold tabular-nums">
            {clock(regularity.mean_midpoint_minutes)}
          </dd>
        </div>
        <div>
          <dt className="opacity-60">Variación típica</dt>
          <dd className="font-bold tabular-nums">±{regularity.sd_minutes} min</dd>
        </div>
      </dl>

      {jetlag ? (
        <div className="mt-4 border-t pt-3" style={{ borderColor: 'var(--mf-line)' }}>
          <h3 className="text-body-sm font-bold">Jet lag social</h3>
          <p className="mt-1 text-body-sm opacity-80">
            Entre semana tu punto medio cae a las{' '}
            <strong className="tabular-nums">{clock(jetlag.weekday_midpoint_minutes)}</strong> y
            el fin de semana a las{' '}
            <strong className="tabular-nums">{clock(jetlag.weekend_midpoint_minutes)}</strong>:{' '}
            <strong>{jetlag.minutes} min</strong> de desfase, como cruzar husos horarios
            cada semana.
          </p>
        </div>
      ) : null}

      <p className="mt-4 text-[11px] opacity-50">
        En 61.000 adultos del UK Biobank, el grupo con horarios más regulares tuvo un 30%
        menos de mortalidad por cualquier causa, y la regularidad predijo mejor que las
        horas dormidas.
      </p>
    </SurfaceCard>
  )
}
