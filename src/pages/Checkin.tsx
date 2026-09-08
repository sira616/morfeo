import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ChatBubble } from '@/components/chat/ChatBubble'
import { ChatComposer } from '@/components/chat/ChatComposer'
import { Button } from '@/components/atoms/Button'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { useCheckinStream } from '@/hooks/useCheckinStream'
import { saveCheckin, type CheckinFields, type Intensity } from '@/api/morfeo'

const MOODS = [
  { value: 1, label: 'Fatal' },
  { value: 2, label: 'Regular' },
  { value: 3, label: 'Normal' },
  { value: 4, label: 'Bien' },
  { value: 5, label: 'Genial' },
]

const INTENSITIES: { value: Intensity; label: string }[] = [
  { value: 'none', label: 'Nada' },
  { value: 'light', label: 'Suave' },
  { value: 'moderate', label: 'Media' },
  { value: 'hard', label: 'Fuerte' },
]

/**
 * Los días desde el último porro van en tramos, no en un número exacto.
 *
 * Nadie recuerda "hace 6 días", y el motor tampoco necesita esa precisión: lo que
 * mira es si estás dentro de la primera semana sin fumar, que es cuando la
 * abstinencia alarga la conciliación.
 */
const CANNABIS_OPTIONS: { label: string; value: number | null }[] = [
  { label: 'No aplica', value: null },
  { label: 'Hoy', value: 0 },
  { label: 'Ayer', value: 1 },
  { label: 'Hace 2-3 días', value: 3 },
  { label: 'Hace 4-7 días', value: 6 },
  { label: 'Hace más de una semana', value: 14 },
  { label: 'Hace más de un mes', value: 40 },
]

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

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="border-t pt-4" style={{ borderColor: 'var(--mf-line)' }}>
      <legend className="px-2 text-body-sm font-bold opacity-70">{title}</legend>
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  )
}

/**
 * El formulario va primero.
 *
 * Es lo único que funciona sin clave de LLM, y enseñar de entrada una pestaña que
 * puede no responder es una forma rara de recibir a alguien. El chat sigue ahí, en la
 * segunda pestaña, y escribe exactamente los mismos campos.
 */
export function CheckinPage() {
  const [tab, setTab] = useState<'form' | 'chat'>('form')

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div className="flex gap-2" role="tablist" aria-label="Modo de check-in">
        <Button
          role="tab"
          aria-selected={tab === 'form'}
          variant={tab === 'form' ? 'primary' : 'ghost'}
          onClick={() => setTab('form')}
        >
          Rellenando
        </Button>
        <Button
          role="tab"
          aria-selected={tab === 'chat'}
          variant={tab === 'chat' ? 'primary' : 'ghost'}
          onClick={() => setTab('chat')}
        >
          Conversando
        </Button>
      </div>

      {tab === 'form' ? <CheckinForm /> : <CheckinChat />}
    </div>
  )
}

function CheckinForm() {
  const queryClient = useQueryClient()
  const [fields, setFields] = useState<CheckinFields>({
    nap_minutes: 0,
    coffees: 0,
    alcohol_units: 0,
    exercise_minutes: 0,
    exercise_intensity: 'none',
    cannabis_days_ago: null,
  })

  const set = <K extends keyof CheckinFields>(key: K, value: CheckinFields[K]) =>
    setFields((f) => ({ ...f, [key]: value }))

  const save = useMutation({
    mutationFn: () => saveCheckin(fields),
    onSuccess: () => {
      // El check-in mueve la recomendación y las asociaciones: si no se invalidan,
      // la portada seguiría enseñando la hora de antes de rellenarlo.
      queryClient.invalidateQueries({ queryKey: ['tonight'] })
      queryClient.invalidateQueries({ queryKey: ['insights'] })
      queryClient.invalidateQueries({ queryKey: ['tips'] })
    },
  })

  return (
    <SurfaceCard className="flex flex-col gap-5">
      <fieldset>
        <legend className="mb-2 text-body-sm font-semibold">¿Qué tal el ánimo hoy?</legend>
        <div className="flex flex-wrap gap-2">
          {MOODS.map((mood) => (
            <Button
              key={mood.value}
              variant={fields.mood === mood.value ? 'primary' : 'ghost'}
              onClick={() => set('mood', mood.value)}
            >
              {mood.label}
            </Button>
          ))}
        </div>
      </fieldset>

      <Section title="Cafeína">
        <Field
          label="Cafés (o equivalentes)"
          hint="La dosis cambia la ventana: uno solo pesa mucho menos que cuatro."
        >
          <input
            type="number"
            min={0}
            max={20}
            value={fields.coffees ?? 0}
            onChange={(e) => set('coffees', Number(e.target.value))}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
        <Field label="Hora del último">
          <input
            type="time"
            value={fields.last_caffeine?.slice(0, 5) ?? ''}
            onChange={(e) =>
              set('last_caffeine', e.target.value ? `${e.target.value}:00` : null)
            }
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
      </Section>

      <Section title="Alcohol y cannabis">
        <Field label="Unidades de alcohol" hint="Una caña, una copa de vino o un chupito.">
          <input
            type="number"
            min={0}
            max={30}
            value={fields.alcohol_units ?? 0}
            onChange={(e) => set('alcohol_units', Number(e.target.value))}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
        <Field label="Último porro" hint="Dejarlo afecta más al sueño que fumarlo.">
          <select
            value={String(fields.cannabis_days_ago ?? '')}
            onChange={(e) =>
              set('cannabis_days_ago', e.target.value === '' ? null : Number(e.target.value))
            }
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          >
            {CANNABIS_OPTIONS.map((option) => (
              <option key={option.label} value={option.value ?? ''}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
      </Section>

      <Section title="Actividad">
        <Field label="Minutos de ejercicio">
          <input
            type="number"
            min={0}
            max={600}
            value={fields.exercise_minutes ?? 0}
            onChange={(e) => set('exercise_minutes', Number(e.target.value))}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
        <Field label="Intensidad">
          <select
            value={fields.exercise_intensity ?? 'none'}
            onChange={(e) => set('exercise_intensity', e.target.value as Intensity)}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          >
            {INTENSITIES.map((i) => (
              <option key={i.value} value={i.value}>
                {i.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Hora a la que terminaste" hint="Solo importa si fue fuerte y muy tarde.">
          <input
            type="time"
            value={fields.exercise_end?.slice(0, 5) ?? ''}
            onChange={(e) => set('exercise_end', e.target.value ? `${e.target.value}:00` : null)}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
        <Field label="Siesta (minutos)">
          <input
            type="number"
            min={0}
            max={300}
            value={fields.nap_minutes ?? 0}
            onChange={(e) => set('nap_minutes', Number(e.target.value))}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
      </Section>

      <Section title="Comidas">
        <Field label="Comidas del día">
          <input
            type="number"
            min={0}
            max={12}
            value={fields.meals ?? ''}
            onChange={(e) => set('meals', e.target.value === '' ? null : Number(e.target.value))}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
        <Field label="Hora de la última" hint="Cenar a menos de tres horas fragmenta la noche.">
          <input
            type="time"
            value={fields.last_meal?.slice(0, 5) ?? ''}
            onChange={(e) => set('last_meal', e.target.value ? `${e.target.value}:00` : null)}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
      </Section>

      <Section title="Mañana">
        <Field label="¿A qué hora te levantas?">
          <input
            type="time"
            value={fields.wake_target?.slice(0, 5) ?? ''}
            onChange={(e) => set('wake_target', e.target.value ? `${e.target.value}:00` : null)}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
        <Field label="Algo que apuntar">
          <input
            type="text"
            maxLength={1000}
            value={fields.notes ?? ''}
            onChange={(e) => set('notes', e.target.value || null)}
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        </Field>
      </Section>

      <Button fullWidth onClick={() => save.mutate()} disabled={save.isPending}>
        {save.isPending ? 'Guardando…' : 'Guardar check-in'}
      </Button>
      {save.isSuccess ? (
        <p role="status" className="text-body-sm" style={{ color: 'var(--mf-good)' }}>
          Guardado. Vuelve a «Esta noche» para ver la hora actualizada.
        </p>
      ) : null}
      {save.isError ? (
        <p role="alert" className="text-body-sm text-error">
          No se pudo guardar. Inténtalo otra vez.
        </p>
      ) : null}
    </SurfaceCard>
  )
}

function CheckinChat() {
  const { messages, extracted, streaming, error, send } = useCheckinStream()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // `scrollIntoView` no existe en todos los entornos (jsdom, por ejemplo). Bajar
    // solo el scroll no vale una excepción que tumbe la conversación entera.
    bottomRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [messages])

  return (
    <>
      <div className="flex flex-col gap-3">
        {messages.length === 0 ? (
          <ChatBubble role="assistant">
            ¿Qué tal ha ido el día? Cuéntame lo que quieras y de paso me entero de un par
            de cosas para calcular tu hora.
          </ChatBubble>
        ) : null}
        {messages.map((message) => (
          <ChatBubble
            key={message.id}
            role={message.role}
            streaming={streaming && message.content === ''}
          >
            {message.content}
          </ChatBubble>
        ))}
        <div ref={bottomRef} />
      </div>

      {error ? (
        <p role="alert" className="text-body-sm text-error">
          {error}
        </p>
      ) : null}

      {Object.keys(extracted).length > 0 ? (
        <SurfaceCard>
          <p className="text-body-sm font-semibold">Apuntado de la conversación</p>
          <ul className="mt-1 text-body-sm opacity-80">
            {Object.entries(extracted).map(([key, value]) => (
              <li key={key}>
                {key}: {value}
              </li>
            ))}
          </ul>
        </SurfaceCard>
      ) : null}

      <ChatComposer onSend={send} disabled={streaming} placeholder="Cuéntame cómo ha ido…" />
    </>
  )
}
