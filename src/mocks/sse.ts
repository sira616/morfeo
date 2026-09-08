import type { CheckinEvent } from '@/lib/events'

function encode(event: CheckinEvent): Uint8Array {
  return new TextEncoder().encode(`data: ${JSON.stringify(event)}\n\n`)
}

/** Reproduce el SSE de `/api/checkin/stream` sin backend ni LLM. */
export function createCheckinSseStream(message: string): ReadableStream<Uint8Array> {
  const events: CheckinEvent[] = [{ node: 'context', data: { turn: 1, known: [] } }]

  const reply = [
    'Vale, apuntado.',
    '',
    `Me dices: “${message.slice(0, 120)}”.`,
    '',
    'Una última cosa: ¿a qué hora tienes que levantarte mañana?',
  ].join('\n')

  for (let i = 0; i < reply.length; i += 24) {
    events.push({ node: 'reply', data: { chunk: reply.slice(i, i + 24) } })
  }

  events.push({
    node: 'extracted',
    data: { fields: { mood: '4', nap_minutes: '0' } },
  })

  return new ReadableStream({
    async start(controller) {
      for (const event of events) {
        controller.enqueue(encode(event))
        await new Promise((r) => setTimeout(r, 25))
      }
      controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n'))
      controller.close()
    },
  })
}
