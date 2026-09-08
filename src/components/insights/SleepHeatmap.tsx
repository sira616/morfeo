import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import type { HeatmapNight } from '@/api/morfeo'

const WEEKS = 8
const DAYS = WEEKS * 7
const WEEKDAYS = ['L', 'M', 'X', 'J', 'V', 'S', 'D']

function isoDay(date: Date): string {
  return date.toISOString().slice(0, 10)
}

/** Lunes de la semana en que empieza la cuadrícula. */
function gridStart(today: Date): Date {
  const start = new Date(today)
  start.setDate(start.getDate() - (DAYS - 1))
  // getDay(): 0 es domingo. La semana europea empieza en lunes.
  start.setDate(start.getDate() - ((start.getDay() + 6) % 7))
  return start
}

/**
 * Verde proporcional a la eficiencia, con dos umbrales.
 *
 * Por debajo del 85% se tiñe de ámbar en vez de verde pálido: es el umbral con el que
 * el motor decide comprimir la ventana, y verlo en la cuadrícula explica por qué.
 */
function cellStyle(efficiency: number | undefined) {
  if (efficiency === undefined) {
    return { background: 'var(--mf-line)', opacity: 0.35 }
  }
  if (efficiency < 0.85) {
    const t = Math.max(0, Math.min(1, (efficiency - 0.6) / 0.25))
    return { background: 'var(--mf-chart-awake)', opacity: 0.3 + 0.6 * t }
  }
  const t = Math.max(0, Math.min(1, (efficiency - 0.85) / 0.13))
  return { background: 'var(--mf-chart-sleep)', opacity: 0.35 + 0.65 * t }
}

export function SleepHeatmap({ nights }: { nights: HeatmapNight[] }) {
  const byDay = new Map(nights.map((n) => [n.night_of, n]))
  const start = gridStart(new Date())

  const columns = Array.from({ length: WEEKS + 1 }, (_, week) =>
    Array.from({ length: 7 }, (_, weekday) => {
      const date = new Date(start)
      date.setDate(date.getDate() + week * 7 + weekday)
      return { key: isoDay(date), night: byDay.get(isoDay(date)), future: date > new Date() }
    }),
  )

  return (
    <SurfaceCard>
      <h2 className="text-headline-sm font-bold">Ocho semanas</h2>
      <p className="mb-3 text-body-sm opacity-70">
        Una casilla por noche, teñida por la eficiencia del sueño.
      </p>

      {/* Rejilla que se estira con la tarjeta en vez de dejar media vacía: las columnas
          reparten el ancho disponible y las casillas quedan cuadradas. */}
      <div className="grid grid-cols-[auto_1fr] gap-2">
        <div className="grid grid-rows-7 gap-1">
          {WEEKDAYS.map((day) => (
            <span key={day} className="flex items-center text-[10px] opacity-50">
              {day}
            </span>
          ))}
        </div>
        <div className="grid grid-flow-col grid-rows-7 gap-1">
          {columns.flat().map((cell) =>
            cell.future ? (
              <span key={cell.key} className="aspect-square" />
            ) : (
              <span
                key={cell.key}
                className="aspect-square rounded-[3px]"
                style={cellStyle(cell.night?.efficiency)}
                title={
                  cell.night
                    ? `${cell.key}: ${Math.round(cell.night.efficiency * 100)}% de eficiencia`
                    : `${cell.key}: sin datos`
                }
              />
            ),
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] opacity-70">
        <Swatch style={cellStyle(undefined)} label="sin datos" />
        <Swatch style={cellStyle(0.7)} label="menos del 85%" />
        <Swatch style={cellStyle(0.9)} label="85% o más" />
        <Swatch style={cellStyle(0.98)} label="excelente" />
      </div>
    </SurfaceCard>
  )
}

function Swatch({ style, label }: { style: React.CSSProperties; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span aria-hidden className="inline-block h-3 w-3 rounded-[3px]" style={style} />
      {label}
    </span>
  )
}
