import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/atoms/Button'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { updateProfile } from '@/api/auth'
import { routes } from '@/router/paths'

/**
 * Tres preguntas y fuera.
 *
 * Sin hora de despertar no hay ancla desde la que calcular hacia atrás, así que este
 * paso no se puede saltar; todo lo demás se aprende luego de los datos del reloj.
 */
export function OnboardingPage() {
  const navigate = useNavigate()
  const [wake, setWake] = useState('07:00')
  const [need, setNeed] = useState(480)
  const [latency, setLatency] = useState(20)
  const [pending, setPending] = useState(false)

  async function finish() {
    setPending(true)
    try {
      await updateProfile({
        default_wake_time: `${wake}:00`,
        sleep_need_minutes: need,
        declared_latency_minutes: latency,
      })
      navigate(routes.tonight, { replace: true })
    } finally {
      setPending(false)
    }
  }

  return (
    <main
      className="grid min-h-dvh place-items-center p-6 text-ink"
      style={{ background: 'var(--mf-canvas-radial)' }}
    >
      <SurfaceCard className="flex w-full max-w-sm flex-col gap-5">
        <h1 className="text-headline-md font-bold">Tres cosas y empezamos</h1>

        <label className="flex flex-col gap-1 text-body-sm font-semibold">
          ¿A qué hora necesitas levantarte entre semana?
          <input
            type="time"
            value={wake}
            onChange={(e) => setWake(e.target.value)}
            className="min-h-touch rounded-md px-3 font-normal"
            style={{ background: 'var(--mf-surf-2)', border: '1px solid var(--mf-line-strong)' }}
          />
        </label>

        <label className="flex flex-col gap-1 text-body-sm font-semibold">
          ¿Cuánto sueño te deja bien? ({Math.floor(need / 60)} h {need % 60} min)
          <input
            type="range"
            min={300}
            max={660}
            step={15}
            value={need}
            onChange={(e) => setNeed(Number(e.target.value))}
          />
        </label>

        <label className="flex flex-col gap-1 text-body-sm font-semibold">
          ¿Cuánto tardas en dormirte una noche normal? ({latency} min)
          <input
            type="range"
            min={0}
            max={120}
            step={5}
            value={latency}
            onChange={(e) => setLatency(Number(e.target.value))}
          />
          <span className="font-normal opacity-70">
            Aquí está la gracia: esos minutos se descuentan de la hora que te digo, para
            que la ventana sea de sueño real y no de estar en la cama.
          </span>
        </label>

        <Button fullWidth onClick={finish} disabled={pending}>
          {pending ? 'Guardando…' : 'Empezar'}
        </Button>
      </SurfaceCard>
    </main>
  )
}
