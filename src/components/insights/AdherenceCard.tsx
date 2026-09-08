import { Flame } from 'lucide-react'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import type { AdherenceNight } from '@/api/morfeo'

const CHART_HEIGHT = 90

/** Minutos desde las 18:00, que es donde empieza el eje. */
function eveningMinutes(time: string): number {
  const [h, m] = time.split(':').map(Number)
  const fromMidnight = (h ?? 0) * 60 + (m ?? 0)
  const shifted = fromMidnight < 12 * 60 ? fromMidnight + 24 * 60 : fromMidnight
  return shifted - 18 * 60
}

/**
 * Recomendado frente a real: el módulo que cierra el bucle.
 *
 * Sin esto la app opina y nadie comprueba nada. El eje empieza a las 18:00 y sigue
 * pasada la medianoche, porque una hora de acostarse a la 01:00 es *más tarde* que una
 * a las 23:00 y en un eje de 0 a 24 saldría al revés.
 */
export function AdherenceCard({
  streak,
  rate,
  series,
}: {
  streak: number
  rate: number | null
  series: AdherenceNight[]
}) {
  const withActual = series.filter((n) => n.actual !== null)
  const values = series.flatMap((n) =>
    [n.recommended, n.actual].filter((v): v is string => v !== null).map(eveningMinutes),
  )
  const min = values.length ? Math.min(...values) - 20 : 0
  const max = values.length ? Math.max(...values) + 20 : 1
  const y = (time: string) => CHART_HEIGHT - ((eveningMinutes(time) - min) / (max - min)) * CHART_HEIGHT

  return (
    <SurfaceCard>
      <h2 className="text-headline-sm font-bold">Recomendado frente a real</h2>
      <p className="mb-3 text-body-sm opacity-70">
        Lo único que dice si el motor acierta.
      </p>

      <div className="flex items-center gap-4">
        <div className="flex items-baseline gap-2">
          <Flame aria-hidden size={20} style={{ color: 'var(--mf-good)' }} />
          <span
            className="text-display-md font-bold tabular-nums"
            style={{ color: 'var(--mf-good)' }}
          >
            {streak}
          </span>
          <span className="text-body-sm opacity-60">
            {streak === 1 ? 'noche seguida' : 'noches seguidas'}
          </span>
        </div>
        {rate !== null ? (
          <div className="ml-auto text-right">
            <p className="text-body-sm opacity-60">La has seguido</p>
            <p className="text-headline-sm font-bold tabular-nums">{Math.round(rate * 100)}%</p>
          </div>
        ) : null}
      </div>

      {withActual.length >= 2 ? (
        <svg
          viewBox={`0 0 ${Math.max(series.length * 10, 100)} ${CHART_HEIGHT}`}
          preserveAspectRatio="none"
          className="mt-4 h-24 w-full"
          role="img"
          aria-label="Comparación entre la hora recomendada y la hora real de acostarse"
        >
          <polyline
            fill="none"
            stroke="var(--mf-chart-recommended)"
            strokeWidth={2}
            strokeDasharray="4 3"
            vectorEffect="non-scaling-stroke"
            points={series.map((n, i) => `${i * 10},${y(n.recommended)}`).join(' ')}
          />
          {series.map((night, i) =>
            night.actual ? (
              <circle
                key={night.day}
                cx={i * 10}
                cy={y(night.actual)}
                r={2.5}
                fill={night.followed === false ? 'var(--mf-chart-awake)' : 'var(--mf-chart-sleep)'}
              />
            ) : null,
          )}
        </svg>
      ) : (
        <p className="mt-4 text-body-sm opacity-70">
          Faltan horas reales de acostarse. Llegan del reloj cuando la exportación las
          trae; hasta entonces solo se puede comparar con lo que marques a mano.
        </p>
      )}
    </SurfaceCard>
  )
}
