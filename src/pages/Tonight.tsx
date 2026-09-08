import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { AlertTriangle, Info } from 'lucide-react'
import { Button } from '@/components/atoms/Button'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { getTonight, markFollowed, type Recommendation } from '@/api/morfeo'
import { routes } from '@/router/paths'

function hhmm(value: string): string {
  return value.slice(0, 5)
}

function duration(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m === 0 ? `${h} h` : `${h} h ${m} min`
}

const CONFIDENCE_COPY: Record<Recommendation['confidence'], string> = {
  baja: 'Con pocas noches medidas todavía. Se afina sola conforme sincronices el reloj.',
  media: 'Basada en unos días de datos.',
  alta: 'Basada en dos semanas o más de noches medidas.',
}

export function TonightPage() {
  const queryClient = useQueryClient()
  const [simulatedWake, setSimulatedWake] = useState<string>('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['tonight', simulatedWake],
    queryFn: () => getTonight(simulatedWake || undefined),
  })

  const follow = useMutation({
    mutationFn: (followed: boolean) => markFollowed(data!.day, followed),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tonight'] }),
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
    <div className="flex flex-col gap-4">
      <SurfaceCard className="text-center">
        <p className="text-body-sm opacity-70">A la cama entre</p>
        <p className="text-display-md font-bold tabular-nums">
          {hhmm(data.window_start)} – {hhmm(data.window_end)}
        </p>
        {/* La distinción que da sentido a la app: la hora es de meterse en la cama. */}
        <p className="mt-2 text-body-sm opacity-80">
          No es la hora de dormirte. Cuentas con {data.onset_latency_minutes} min para
          conciliar, así que dormirías sobre las{' '}
          <strong className="tabular-nums">
            {addMinutes(data.bedtime, data.onset_latency_minutes)}
          </strong>
          .
        </p>
        <p className="mt-3 text-body-sm opacity-70">
          Objetivo: {duration(data.target_sleep_minutes)} de sueño ·{' '}
          {duration(data.time_in_bed_minutes)} en la cama · despertar a{' '}
          {hhmm(data.wake_target)}
        </p>
      </SurfaceCard>

      {data.mode === 'restriccion' ? (
        <SurfaceCard>
          <p className="flex items-start gap-2 text-body-sm">
            <AlertTriangle aria-hidden size={18} className="mt-0.5 shrink-0" />
            <span>
              <strong>Ventana comprimida a propósito.</strong> Puede parecer poco tiempo, y
              es intencionado: mira la explicación de abajo antes de ampliarla por tu cuenta.
            </span>
          </p>
        </SurfaceCard>
      ) : null}

      <SurfaceCard>
        <h2 className="mb-2 text-headline-sm font-bold">Por qué esta hora</h2>
        <ul className="flex flex-col gap-2">
          {data.factors.map((factor) => (
            <li key={factor.label} className="flex items-baseline justify-between gap-3">
              <span>
                <strong>{factor.label}</strong>
                <span className="block text-body-sm opacity-70">{factor.detail}</span>
              </span>
              <span className="shrink-0 tabular-nums">
                {factor.minutes > 0 ? '+' : ''}
                {factor.minutes} min
              </span>
            </li>
          ))}
        </ul>
        {data.notes.length > 0 ? (
          <ul className="mt-3 flex flex-col gap-2 border-t pt-3" style={{ borderColor: 'var(--mf-line)' }}>
            {data.notes.map((note) => (
              <li key={note} className="flex items-start gap-2 text-body-sm">
                <Info aria-hidden size={16} className="mt-0.5 shrink-0" />
                {note}
              </li>
            ))}
          </ul>
        ) : null}
        <p className="mt-3 text-body-sm opacity-70">
          Confianza {data.confidence}. {CONFIDENCE_COPY[data.confidence]}
        </p>
      </SurfaceCard>

      <SurfaceCard>
        <label htmlFor="wake" className="text-body-sm font-semibold">
          ¿Y si mañana te levantas a otra hora?
        </label>
        <p className="mb-2 text-body-sm opacity-70">
          Solo simula: no cambia tu perfil ni se guarda.
        </p>
        <div className="flex gap-2">
          <input
            id="wake"
            type="time"
            value={simulatedWake ? simulatedWake.slice(0, 5) : ''}
            onChange={(e) => setSimulatedWake(e.target.value ? `${e.target.value}:00` : '')}
            className="min-h-touch flex-1 rounded-md px-3"
            style={{ background: 'var(--mf-surf-2)', border: '1px solid var(--mf-line-strong)' }}
          />
          <Button variant="ghost" onClick={() => setSimulatedWake('')} disabled={!simulatedWake}>
            Quitar
          </Button>
        </div>
      </SurfaceCard>

      {!simulatedWake ? (
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
      ) : null}

      <Link to={routes.checkin} className="text-center text-body-sm underline">
        Contarle cómo ha ido el día
      </Link>
    </div>
  )
}

/** Suma minutos a un "HH:MM:SS" y devuelve "HH:MM", cruzando medianoche. */
function addMinutes(time: string, minutes: number): string {
  const [h, m] = time.split(':').map(Number)
  const total = ((h ?? 0) * 60 + (m ?? 0) + minutes + 1440) % 1440
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}
