import { useQuery } from '@tanstack/react-query'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { SleepHeatmap } from '@/components/insights/SleepHeatmap'
import { RegularityCard } from '@/components/insights/RegularityCard'
import { AssociationsCard } from '@/components/insights/AssociationsCard'
import { AdherenceCard } from '@/components/insights/AdherenceCard'
import { getInsights, getNights, type Night } from '@/api/morfeo'

const CHART_HEIGHT = 120
const BAR_GAP = 2

function duration(minutes: number): string {
  return `${Math.floor(minutes / 60)} h ${String(minutes % 60).padStart(2, '0')}`
}

/**
 * Gráfica en SVG a mano, sin librería.
 *
 * Son dos series y treinta barras: meter una dependencia de charting para esto
 * pesaría más en el bundle que toda la página.
 */
function SleepChart({ nights }: { nights: Night[] }) {
  if (nights.length === 0) return null

  const max = Math.max(...nights.map((n) => n.time_in_bed_minutes), 480)
  const barWidth = 100 / nights.length

  return (
    <svg
      viewBox={`0 0 100 ${CHART_HEIGHT}`}
      preserveAspectRatio="none"
      className="h-32 w-full"
      role="img"
      aria-label={`Sueño de las últimas ${nights.length} noches`}
    >
      {nights.map((night, index) => {
        const x = index * barWidth
        const inBed = (night.time_in_bed_minutes / max) * CHART_HEIGHT
        const slept = (night.total_sleep_minutes / max) * CHART_HEIGHT
        return (
          <g key={night.night_of}>
            {/* Barra clara: tiempo en la cama. Barra sólida: sueño real. La
                diferencia entre ambas es, visualmente, la eficiencia. */}
            <rect
              x={x}
              y={CHART_HEIGHT - inBed}
              width={barWidth - BAR_GAP}
              height={inBed}
              fill="var(--mf-chart-in-bed)"
            />
            <rect
              x={x}
              y={CHART_HEIGHT - slept}
              width={barWidth - BAR_GAP}
              height={slept}
              fill="var(--mf-chart-sleep)"
            />
          </g>
        )
      })}
    </svg>
  )
}

/**
 * Aquí sí toca densidad. La portada dice una cosa; esta pantalla es para mirar
 * patrones, y para eso hacen falta varios módulos a la vez.
 */
export function HistoryPage() {
  const { data: nights = [], isLoading } = useQuery({
    queryKey: ['nights'],
    queryFn: () => getNights(30),
  })
  const { data: insights } = useQuery({ queryKey: ['insights'], queryFn: getInsights })

  if (isLoading) return <p className="py-8 text-center opacity-70">Cargando…</p>

  if (nights.length === 0) {
    return (
      <SurfaceCard className="text-center">
        <p>Todavía no hay noches registradas.</p>
        <p className="mt-1 text-body-sm opacity-70">
          Sincroniza el reloj o importa una exportación desde «Reloj».
        </p>
      </SurfaceCard>
    )
  }

  const avgSleep = Math.round(
    nights.reduce((sum, n) => sum + n.total_sleep_minutes, 0) / nights.length,
  )
  const avgEfficiency = nights.reduce((sum, n) => sum + n.efficiency, 0) / nights.length

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-6 lg:grid-cols-3">
        <Stat label="Sueño medio" value={duration(avgSleep)} />
        <Stat
          label="Eficiencia media"
          value={`${Math.round(avgEfficiency * 100)}%`}
          good={avgEfficiency >= 0.85}
        />
        <Stat
          label="Noches medidas"
          value={String(nights.length)}
          hint="de las últimas 30"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <SurfaceCard>
          <h2 className="mb-2 text-headline-sm font-bold">Últimas {nights.length} noches</h2>
          <SleepChart nights={nights} />
          {/* Esta es la eficiencia clásica, la que reporta el reloj. El motor usa una
              variante que descuenta la latencia, así que no se promete aquí lo que va a
              decidir: esa decisión, con su propio número, se explica en «Esta noche». */}
          <p className="mt-3 text-body-sm opacity-70">
            Eficiencia clásica: dormido frente al tiempo total en la cama, incluidos los
            minutos que tardas en dormirte. El motor descuenta esa latencia para decidir
            la ventana, así que su número no coincide exactamente con este.
          </p>
        </SurfaceCard>

        {insights ? <RegularityCard regularity={insights.regularity} /> : null}
      </div>

      {insights ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <AssociationsCard associations={insights.associations} />
          <SleepHeatmap nights={insights.heatmap} />
          <AdherenceCard
            streak={insights.adherence.streak}
            rate={insights.adherence.rate}
            series={insights.adherence.series}
          />
        </div>
      ) : null}

      <SurfaceCard padded={false}>
        <table className="w-full text-body-sm">
          <caption className="sr-only">Detalle por noche</caption>
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--mf-line)' }}>
              <th scope="col" className="p-2 text-left">Noche</th>
              <th scope="col" className="p-2 text-right">Dormido</th>
              <th scope="col" className="p-2 text-right">En cama</th>
              <th scope="col" className="p-2 text-right">Efic.</th>
            </tr>
          </thead>
          <tbody>
            {[...nights].reverse().map((night) => (
              <tr
                key={night.night_of}
                className="border-b"
                style={{ borderColor: 'var(--mf-line)' }}
              >
                <th scope="row" className="p-2 text-left font-normal">
                  {night.night_of}
                </th>
                <td className="p-2 text-right tabular-nums">
                  {duration(night.total_sleep_minutes)}
                </td>
                <td className="p-2 text-right tabular-nums">
                  {duration(night.time_in_bed_minutes)}
                </td>
                <td
                  className="p-2 text-right tabular-nums"
                  // Se compara sobre el valor redondeado, el mismo que se enseña: si no,
                  // una noche al 84,9% aparece como "85%" y sin el verde.
                  style={{
                    color:
                      Math.round(night.efficiency * 100) >= 85 ? 'var(--mf-good)' : undefined,
                  }}
                >
                  {Math.round(night.efficiency * 100)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </SurfaceCard>
    </div>
  )
}

function Stat({
  label,
  value,
  hint,
  good,
}: {
  label: string
  value: string
  hint?: string
  good?: boolean
}) {
  return (
    <SurfaceCard>
      <p className="text-body-sm opacity-60">{label}</p>
      <p
        className="text-display-md font-bold tabular-nums"
        style={good ? { color: 'var(--mf-good)' } : undefined}
      >
        {value}
      </p>
      {hint ? <p className="text-body-sm opacity-50">{hint}</p> : null}
    </SurfaceCard>
  )
}
