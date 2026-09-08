import type { Recommendation } from '@/api/morfeo'

const CX = 150
const CY = 148
const R = 120
const STROKE = 18

function polar(angleDeg: number, radius = R): [number, number] {
  const a = (angleDeg * Math.PI) / 180
  return [CX + radius * Math.cos(a), CY + radius * Math.sin(a)]
}

/** Arco entre dos ángulos, recorriendo la mitad superior de izquierda a derecha. */
function arc(startDeg: number, endDeg: number): string {
  const [x1, y1] = polar(startDeg)
  const [x2, y2] = polar(endDeg)
  return `M ${x1} ${y1} A ${R} ${R} 0 ${endDeg - startDeg > 180 ? 1 : 0} 1 ${x2} ${y2}`
}

function hhmm(value: string): string {
  return value.slice(0, 5)
}

function addMinutes(time: string, minutes: number): string {
  const [h, m] = time.split(':').map(Number)
  const total = ((h ?? 0) * 60 + (m ?? 0) + minutes + 1440) % 1440
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}

function duration(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m === 0 ? `${h} h` : `${h} h ${m} min`
}

/**
 * La noche recomendada como un arco, con las franjas proporcionales al tiempo real.
 *
 * Es lo que convierte "23:35" en algo que se entiende sin leer: se ve de un golpe que
 * el trozo ámbar del principio (lo que tardas en dormirte) no es sueño, que es
 * justamente la idea que la app intenta meter en la cabeza.
 *
 * SVG a mano y sin librería: son tres segmentos de círculo.
 */
export function NightArc({ recommendation }: { recommendation: Recommendation }) {
  const { onset_latency_minutes: latency, sleep_window_minutes: inBed } = recommendation
  const targetSleep = Math.min(recommendation.target_sleep_minutes, inBed)
  const restlessness = Math.max(0, inBed - targetSleep)
  const total = latency + inBed

  // 180° = meterse en la cama (izquierda); 360° = despertar (derecha).
  const span = (minutes: number) => (minutes / total) * 180
  const latencyEnd = 180 + span(latency)
  const sleepEnd = latencyEnd + span(targetSleep)

  const asleepAt = addMinutes(recommendation.bedtime, latency)

  const segments = [
    { d: arc(180, latencyEnd), color: 'var(--mf-chart-awake)', label: 'conciliación' },
    { d: arc(latencyEnd, sleepEnd), color: 'var(--mf-chart-sleep)', label: 'sueño' },
    ...(restlessness > 0
      ? [{ d: arc(sleepEnd, 360), color: 'var(--mf-chart-in-bed)', label: 'vigilia en cama' }]
      : []),
  ]

  return (
    <figure className="m-0 flex flex-col items-center">
      <svg
        viewBox="0 0 300 175"
        className="w-full max-w-sm"
        role="img"
        aria-label={
          `Te acuestas a las ${hhmm(recommendation.bedtime)}, tardas ${latency} minutos en ` +
          `dormirte, duermes ${duration(targetSleep)} y te levantas a las ` +
          `${hhmm(recommendation.wake_target)}.`
        }
      >
        {/* Carril de fondo: da forma al arco aunque un segmento sea diminuto. */}
        <path
          d={arc(180, 360)}
          fill="none"
          stroke="var(--mf-line)"
          strokeWidth={STROKE}
          strokeLinecap="round"
        />
        {segments.map((segment) => (
          <path
            key={segment.label}
            d={segment.d}
            fill="none"
            stroke={segment.color}
            strokeWidth={STROKE}
            strokeLinecap="butt"
          />
        ))}

        <text
          x={CX - R}
          y={CY + 24}
          textAnchor="middle"
          className="fill-ink-dim text-[11px]"
        >
          {hhmm(recommendation.bedtime)}
        </text>
        <text
          x={CX + R}
          y={CY + 24}
          textAnchor="middle"
          className="fill-ink-dim text-[11px]"
        >
          {hhmm(recommendation.wake_target)}
        </text>

        <text x={CX} y={CY - 46} textAnchor="middle" className="fill-ink-dim text-[11px]">
          te duermes sobre las
        </text>
        <text x={CX} y={CY - 18} textAnchor="middle" className="fill-ink text-[26px] font-bold">
          {asleepAt}
        </text>
      </svg>

      <figcaption className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1 text-body-sm">
        <Legend color="var(--mf-chart-awake)" label={`${latency} min conciliando`} />
        <Legend color="var(--mf-chart-sleep)" label={`${duration(targetSleep)} de sueño`} />
        {restlessness > 0 ? (
          <Legend color="var(--mf-chart-in-bed)" label={`${restlessness} min de vigilia`} />
        ) : null}
      </figcaption>
    </figure>
  )
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5 opacity-80">
      <span
        aria-hidden
        className="inline-block h-2.5 w-2.5 rounded-full"
        style={{ background: color }}
      />
      {label}
    </span>
  )
}
