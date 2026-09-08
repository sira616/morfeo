import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ChatBubble } from '@/components/chat/ChatBubble'
import { ChatComposer } from '@/components/chat/ChatComposer'
import { Button } from '@/components/atoms/Button'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { useCheckinStream } from '@/hooks/useCheckinStream'
import { saveCheckin, type CheckinFields } from '@/api/morfeo'

const MOODS = [
  { value: 1, label: 'Fatal' },
  { value: 2, label: 'Regular' },
  { value: 3, label: 'Normal' },
  { value: 4, label: 'Bien' },
  { value: 5, label: 'Genial' },
]

/**
 * Dos formas de hacer el mismo check-in.
 *
 * El chat es lo bonito, pero hay noches en que nadie quiere conversar, y perder el
 * dato por eso sería absurdo. El formulario escribe exactamente los mismos campos.
 */
export function CheckinPage() {
  const [tab, setTab] = useState<'chat' | 'form'>('chat')
  const { messages, extracted, streaming, error, send } = useCheckinStream()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2" role="tablist" aria-label="Modo de check-in">
        <Button
          role="tab"
          aria-selected={tab === 'chat'}
          variant={tab === 'chat' ? 'primary' : 'ghost'}
          onClick={() => setTab('chat')}
        >
          Conversando
        </Button>
        <Button
          role="tab"
          aria-selected={tab === 'form'}
          variant={tab === 'form' ? 'primary' : 'ghost'}
          onClick={() => setTab('form')}
        >
          Rellenando
        </Button>
      </div>

      {tab === 'chat' ? (
        <>
          <div className="flex flex-col gap-3">
            {messages.length === 0 ? (
              <ChatBubble role="assistant">
                ¿Qué tal ha ido el día? Cuéntame lo que quieras y de paso me entero de un
                par de cosas para calcular tu hora.
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

          <ChatComposer
            onSend={send}
            disabled={streaming}
            placeholder="Cuéntame cómo ha ido…"
          />
        </>
      ) : (
        <CheckinForm />
      )}
    </div>
  )
}

function CheckinForm() {
  const queryClient = useQueryClient()
  const [fields, setFields] = useState<CheckinFields>({ nap_minutes: 0, alcohol: false })

  const save = useMutation({
    mutationFn: () => saveCheckin(fields),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tonight'] }),
  })

  return (
    <SurfaceCard className="flex flex-col gap-4">
      <fieldset>
        <legend className="mb-2 text-body-sm font-semibold">¿Qué tal el ánimo hoy?</legend>
        <div className="flex flex-wrap gap-2">
          {MOODS.map((mood) => (
            <Button
              key={mood.value}
              variant={fields.mood === mood.value ? 'primary' : 'ghost'}
              onClick={() => setFields((f) => ({ ...f, mood: mood.value }))}
            >
              {mood.label}
            </Button>
          ))}
        </div>
      </fieldset>

      <label className="flex flex-col gap-1 text-body-sm font-semibold">
        Siesta hoy (minutos)
        <input
          type="number"
          min={0}
          max={300}
          value={fields.nap_minutes ?? 0}
          onChange={(e) => setFields((f) => ({ ...f, nap_minutes: Number(e.target.value) }))}
          className="min-h-touch rounded-md px-3 font-normal"
          style={{ background: 'var(--mf-surf-2)', border: '1px solid var(--mf-line-strong)' }}
        />
      </label>

      <label className="flex flex-col gap-1 text-body-sm font-semibold">
        Último café o bebida con cafeína
        <input
          type="time"
          value={fields.last_caffeine?.slice(0, 5) ?? ''}
          onChange={(e) =>
            setFields((f) => ({
              ...f,
              last_caffeine: e.target.value ? `${e.target.value}:00` : null,
            }))
          }
          className="min-h-touch rounded-md px-3 font-normal"
          style={{ background: 'var(--mf-surf-2)', border: '1px solid var(--mf-line-strong)' }}
        />
      </label>

      <label className="flex items-center gap-2 text-body-sm font-semibold">
        <input
          type="checkbox"
          checked={fields.alcohol ?? false}
          onChange={(e) => setFields((f) => ({ ...f, alcohol: e.target.checked }))}
        />
        He bebido alcohol hoy
      </label>

      <label className="flex flex-col gap-1 text-body-sm font-semibold">
        ¿A qué hora te levantas mañana?
        <input
          type="time"
          value={fields.wake_target?.slice(0, 5) ?? ''}
          onChange={(e) =>
            setFields((f) => ({
              ...f,
              wake_target: e.target.value ? `${e.target.value}:00` : null,
            }))
          }
          className="min-h-touch rounded-md px-3 font-normal"
          style={{ background: 'var(--mf-surf-2)', border: '1px solid var(--mf-line-strong)' }}
        />
      </label>

      <Button fullWidth onClick={() => save.mutate()} disabled={save.isPending}>
        {save.isPending ? 'Guardando…' : 'Guardar check-in'}
      </Button>
      {save.isSuccess ? (
        <p role="status" className="text-body-sm opacity-80">
          Guardado. Vuelve a «Esta noche» para ver la hora actualizada.
        </p>
      ) : null}
    </SurfaceCard>
  )
}
