import { useState, type ReactNode } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/atoms/Button'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { saveNight } from '@/api/morfeo'
import { ApiError } from '@/lib/apiClient'

const inputStyle = {
  background: 'var(--mf-surf-2)',
  border: '1px solid var(--mf-line-strong)',
} as const

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-body-sm font-semibold">
      {label}
      {children}
      {hint ? <span className="font-normal opacity-60">{hint}</span> : null}
    </label>
  )
}

/** Minutos entre dos horas "HH:MM", cruzando medianoche. */
function minutesBetween(from: string, to: string): number {
  const [fh, fm] = from.split(':').map(Number)
  const [th, tm] = to.split(':').map(Number)
  const start = (fh ?? 0) * 60 + (fm ?? 0)
  const end = (th ?? 0) * 60 + (tm ?? 0)
  return end >= start ? end - start : end + 1440 - start
}

/** Fecha de la noche: la del día en que uno se acuesta, como la cuenta la gente. */
function nightOf(bedTime: string): string {
  const now = new Date()
  const [h] = bedTime.split(':').map(Number)
  // Acostarse de madrugada (antes de las 12) cuenta como la noche del día anterior.
  if ((h ?? 0) < 12) now.setDate(now.getDate() - 1)
  return now.toISOString().slice(0, 10)
}

/**
 * Registro manual de una noche.
 *
 * Nadie sabe cuántos minutos durmió, así que no se pregunta: se piden las horas a las
 * que se acostó y se levantó, lo que tardó en dormirse y el rato que estuvo despierta,
 * y de ahí salen el tiempo en la cama y el sueño total. Es la misma cuenta que hace un
 * reloj, solo que con datos que una persona sí puede responder.
 */
export function NightLogForm({ onSaved }: { onSaved?: () => void } = {}) {
  const queryClient = useQueryClient()
  const [bedAt, setBedAt] = useState('23:30')
  const [wakeAt, setWakeAt] = useState('07:00')
  const [latency, setLatency] = useState(20)
  const [awakeMinutes, setAwakeMinutes] = useState(0)
  const [awakenings, setAwakenings] = useState(0)

  const timeInBed = minutesBetween(bedAt, wakeAt)
  const totalSleep = timeInBed - latency - awakeMinutes
  const valid = totalSleep > 0

  const save = useMutation({
    mutationFn: () =>
      saveNight({
        night_of: nightOf(bedAt),
        total_sleep_minutes: totalSleep,
        time_in_bed_minutes: timeInBed,
        onset_latency_minutes: latency,
        awakenings,
        bed_at: `${nightOf(bedAt)}T${bedAt}:00`,
      }),
    onSuccess: () => {
      // La noche cambia el perfil observado, y con él la recomendación y las métricas.
      for (const key of ['tonight', 'nights', 'insights', 'tips']) {
        queryClient.invalidateQueries({ queryKey: [key] })
      }
      onSaved?.()
    },
  })

  return (
    <SurfaceCard className="flex flex-col gap-5">
      <div>
        <h2 className="text-headline-sm font-bold">¿Cómo ha ido la noche?</h2>
        <p className="mt-1 text-body-sm opacity-70">
          Con esto Morfeo aprende tu latencia y tu eficiencia reales, que es lo que hace
          que la hora deje de ser una estimación genérica. No hace falta reloj.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="¿A qué hora te acostaste?">
          <input
            type="time"
            value={bedAt}
            onChange={(e) => setBedAt(e.target.value)}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
        <Field label="¿A qué hora te levantaste?">
          <input
            type="time"
            value={wakeAt}
            onChange={(e) => setWakeAt(e.target.value)}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
        <Field
          label="¿Cuánto tardaste en dormirte? (min)"
          hint="A ojo vale. Es el dato que separa acostarse de dormir."
        >
          <input
            type="number"
            min={0}
            max={600}
            value={latency}
            onChange={(e) => setLatency(Number(e.target.value))}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
        <Field label="¿Cuánto estuviste despierta de madrugada? (min)">
          <input
            type="number"
            min={0}
            max={600}
            value={awakeMinutes}
            onChange={(e) => setAwakeMinutes(Number(e.target.value))}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
        <Field label="¿Cuántas veces te despertaste?">
          <input
            type="number"
            min={0}
            max={50}
            value={awakenings}
            onChange={(e) => setAwakenings(Number(e.target.value))}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
      </div>

      {/* El resultado se enseña antes de guardar: si sale algo raro, se ve aquí y no
          tres pantallas después en una media del historial. */}
      <div
        className="rounded-lg p-3 text-body-sm"
        style={{ background: 'var(--mf-surf-2)' }}
        role="status"
      >
        {valid ? (
          <>
            <strong>{Math.floor(totalSleep / 60)} h {String(totalSleep % 60).padStart(2, '0')}</strong>{' '}
            de sueño sobre {Math.floor(timeInBed / 60)} h {String(timeInBed % 60).padStart(2, '0')} en
            la cama · eficiencia{' '}
            <strong style={{ color: totalSleep / timeInBed >= 0.85 ? 'var(--mf-good)' : undefined }}>
              {Math.round((totalSleep / timeInBed) * 100)}%
            </strong>
          </>
        ) : (
          <span style={{ color: 'var(--mf-chart-awake)' }}>
            Con esas horas no queda tiempo dormido. Revisa la hora de acostarte o los
            minutos despierta.
          </span>
        )}
      </div>

      <Button fullWidth onClick={() => save.mutate()} disabled={!valid || save.isPending}>
        {save.isPending ? 'Guardando…' : 'Guardar la noche'}
      </Button>

      {save.isSuccess ? (
        <p role="status" className="text-body-sm" style={{ color: 'var(--mf-good)' }}>
          Guardada. La recomendación de esta noche ya la tiene en cuenta.
        </p>
      ) : null}
      {save.isError ? (
        <p role="alert" className="text-body-sm text-error">
          {save.error instanceof ApiError ? save.error.message : 'No se pudo guardar.'}
        </p>
      ) : null}
    </SurfaceCard>
  )
}
