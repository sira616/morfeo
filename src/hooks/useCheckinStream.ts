import { useCallback, useEffect, useRef, useState } from 'react'
import type { CheckinEvent } from '@/lib/events'
import { useAuthStore } from '@/stores/authStore'

export type CheckinMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

/**
 * Consume el SSE de `/api/checkin/stream`.
 *
 * El historial se manda en cada petición en lugar de guardarlo en servidor: el
 * check-in es corto y se agota en una sesión, así no hay estado que expirar.
 */
export function useCheckinStream() {
  const [messages, setMessages] = useState<CheckinMessage[]>([])
  const [extracted, setExtracted] = useState<Record<string, string>>({})
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Ref espejo del estado: `send` se memoiza con dependencias vacías para no
  // recrearse en cada tecla, así que no puede leer `messages` directamente.
  const messagesRef = useRef<CheckinMessage[]>([])
  useEffect(() => {
    messagesRef.current = messages
  }, [messages])


  const reset = useCallback(() => {
    abortRef.current?.abort()
    setMessages([])
    setExtracted({})
    setStreaming(false)
    setError(null)
  }, [])

  const send = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed) return

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    const history = messagesRef.current.map((m) => ({
      role: m.role,
      content: m.content,
    }))
    const assistantId = `a-${Date.now()}`
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: 'user', content: trimmed },
      { id: assistantId, role: 'assistant', content: '' },
    ])
    setStreaming(true)
    setError(null)

    const token = useAuthStore.getState().accessToken
    try {
      const response = await fetch(`${API_BASE}/api/checkin/stream`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          Accept: 'text/event-stream',
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message: trimmed, history }),
        signal: controller.signal,
      })

      if (!response.ok || !response.body) {
        throw new Error('checkin-stream-failed')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''

        for (const part of parts) {
          const dataLine = part.split('\n').find((line) => line.startsWith('data:'))
          if (!dataLine) continue
          const raw = dataLine.slice(5).trim()
          if (!raw || raw === '[DONE]') continue

          let event: CheckinEvent
          try {
            event = JSON.parse(raw) as CheckinEvent
          } catch {
            continue
          }

          if (event.node === 'reply') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: m.content + event.data.chunk } : m,
              ),
            )
          } else if (event.node === 'extracted') {
            setExtracted((prev) => ({ ...prev, ...event.data.fields }))
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      setError('No se pudo continuar el check-in. Inténtalo de nuevo.')
    } finally {
      setStreaming(false)
    }
  }, [])

  return { messages, extracted, streaming, error, send, reset }
}
