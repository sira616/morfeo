import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import type { Association } from '@/api/morfeo'

function duration(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h === 0 ? `${m} min` : `${h} h ${String(m).padStart(2, '0')}`
}

/**
 * Qué acompaña a las buenas y a las malas noches de esta persona.
 *
 * Sustituye al jet lag social, que era una media de población: esto habla de sus
 * propios datos. El backend ya filtra los factores sin noches suficientes a los dos
 * lados, así que aquí solo llega lo que tiene algo detrás.
 *
 * El aviso de que es asociación y no causa no es letra pequeña por cumplir: son los
 * datos de una sola persona, sin control de nada, y la tentación de leerlo como una
 * relación causal es exactamente lo que hay que frenar.
 */
export function AssociationsCard({ associations }: { associations: Association[] }) {
  if (associations.length === 0) {
    return (
      <SurfaceCard>
        <h2 className="text-headline-sm font-bold">Qué acompaña a tus mejores noches</h2>
        <p className="mt-2 text-body-sm opacity-70">
          Hacen falta al menos tres noches con cada hábito y tres sin él. Cuantos más
          check-ins rellenes, antes aparece: es la parte de la app que aprende de ti en
          vez de contarte medias de población.
        </p>
      </SurfaceCard>
    )
  }

  const worst = Math.max(...associations.map((a) => Math.abs(a.delta_sleep_minutes)))

  return (
    <SurfaceCard>
      <h2 className="text-headline-sm font-bold">Qué acompaña a tus mejores noches</h2>
      <p className="mb-4 text-body-sm opacity-70">
        Comparando tus noches con y sin cada hábito.
      </p>

      <ul className="flex flex-col gap-4">
        {associations.map((a) => {
          const worse = a.delta_sleep_minutes < 0
          const width = Math.round((Math.abs(a.delta_sleep_minutes) / worst) * 100)
          return (
            <li key={a.key}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-body-sm font-bold">Con {a.label}</span>
                <span
                  className="shrink-0 tabular-nums"
                  style={{ color: worse ? 'var(--mf-chart-awake)' : 'var(--mf-good)' }}
                >
                  {worse ? '−' : '+'}
                  {duration(Math.abs(a.delta_sleep_minutes))}
                </span>
              </div>
              <div
                className="mt-1 h-1.5 w-full overflow-hidden rounded-full"
                style={{ background: 'var(--mf-line)' }}
              >
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${width}%`,
                    background: worse ? 'var(--mf-chart-awake)' : 'var(--mf-good)',
                  }}
                />
              </div>
              <p className="mt-1 text-body-sm opacity-60">
                {duration(a.mean_sleep_with)} de media en {a.nights_with}{' '}
                {a.nights_with === 1 ? 'noche' : 'noches'}, frente a{' '}
                {duration(a.mean_sleep_without)} en las {a.nights_without} sin.
              </p>
            </li>
          )
        })}
      </ul>

      <p className="mt-4 text-[11px] opacity-50">
        Son asociaciones, no causas: tus datos, sin control de nada más. Sirven para
        saber dónde fijarte, no para concluir.
      </p>
    </SurfaceCard>
  )
}
