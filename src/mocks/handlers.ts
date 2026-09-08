import { HttpResponse, http } from 'msw'
import {
  mockDevUserDetail,
  mockDevUsers,
  mockInsights,
  mockNights,
  mockRecommendation,
  mockTips,
  mockUser,
} from '@/mocks/fixtures'
import { createCheckinSseStream } from '@/mocks/sse'
import type { Night, Recommendation } from '@/api/morfeo'

/**
 * Mocks de la API. Cubren el recorrido entero para poder desarrollar el frontend sin
 * backend, sin Supabase y sin clave de LLM.
 *
 * El estado vive en estos módulos y se reinicia al recargar: es intencionado, no hay
 * nada que persistir aquí.
 */
let user = { ...mockUser }
let nights: Night[] = [...mockNights]
let recommendation: Recommendation = { ...mockRecommendation }

// Palanca para los tests: fuerza que el siguiente refresco falle, que es la unica
// forma de comprobar que apiClient cierra la sesion en vez de reintentar en bucle.
let failNextRefresh = false

export function __failNextRefresh() {
  failNextRefresh = true
}

function unauthorized(request: Request) {
  return !request.headers.get('Authorization')
}

export const handlers = [
  http.post('/api/auth/register', async ({ request }) => {
    const body = (await request.json()) as { email: string }
    return HttpResponse.json({ id: 'user-demo', email: body.email }, { status: 201 })
  }),

  http.post('/api/auth/login', async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string }
    if (!body.password) {
      return HttpResponse.json({ detail: 'Credenciales inválidas' }, { status: 401 })
    }
    user = { ...user, email: body.email }
    return HttpResponse.json({
      access_token: 'mock-access',
      refresh_token: 'mock-refresh',
      user,
    })
  }),

  http.post('/api/auth/refresh', () => {
    if (failNextRefresh) {
      failNextRefresh = false
      return HttpResponse.json({ detail: 'Refresh token invalido' }, { status: 401 })
    }
    return HttpResponse.json({
      access_token: 'mock-access-2',
      refresh_token: 'mock-refresh-2',
    })
  }),

  http.post('/api/auth/logout', () => new HttpResponse(null, { status: 204 })),

  http.get('/api/me', ({ request }) =>
    unauthorized(request)
      ? HttpResponse.json({ detail: 'No autenticado' }, { status: 401 })
      : HttpResponse.json(user),
  ),

  http.patch('/api/me', async ({ request }) => {
    if (unauthorized(request)) {
      return HttpResponse.json({ detail: 'No autenticado' }, { status: 401 })
    }
    const patch = (await request.json()) as Record<string, unknown>
    user = {
      ...user,
      onboardingDone: true,
      displayName: (patch.display_name as string) ?? user.displayName,
      defaultWakeTime: (patch.default_wake_time as string) ?? user.defaultWakeTime,
      sleepNeedMinutes: (patch.sleep_need_minutes as number) ?? user.sleepNeedMinutes,
      declaredLatencyMinutes:
        (patch.declared_latency_minutes as number) ?? user.declaredLatencyMinutes,
    }
    return HttpResponse.json(user)
  }),

  http.get('/api/bedtime/tonight', ({ request }) => {
    if (unauthorized(request)) {
      return HttpResponse.json({ detail: 'No autenticado' }, { status: 401 })
    }
    const wake = new URL(request.url).searchParams.get('wake_target')
    return HttpResponse.json(
      wake ? { ...recommendation, wake_target: wake } : recommendation,
    )
  }),

  http.get('/api/bedtime/history', ({ request }) =>
    unauthorized(request)
      ? HttpResponse.json({ detail: 'No autenticado' }, { status: 401 })
      : HttpResponse.json([recommendation]),
  ),

  http.patch('/api/bedtime/:day/followed', async ({ request }) => {
    const body = (await request.json()) as { followed: boolean }
    recommendation = { ...recommendation, followed: body.followed }
    return new HttpResponse(null, { status: 204 })
  }),

  http.get('/api/sleep/nights', ({ request }) => {
    if (unauthorized(request)) {
      return HttpResponse.json({ detail: 'No autenticado' }, { status: 401 })
    }
    // El backend respeta `days`; el mock también, o la pantalla miente sobre cuántas
    // noches está enseñando.
    const days = Number(new URL(request.url).searchParams.get('days') ?? 30)
    // Las más recientes, sin romper el orden ascendente que da el backend.
    return HttpResponse.json(nights.slice(-days))
  }),

  http.post('/api/sleep/import', async ({ request }) => {
    const body = (await request.json()) as { content: string; format: string }
    try {
      const parsed = JSON.parse(body.content) as Night[]
      nights = parsed.map((n) => ({
        ...n,
        efficiency: Number((n.total_sleep_minutes / n.time_in_bed_minutes).toFixed(3)),
        source: 'import',
      }))
      return HttpResponse.json({ written: nights.length, from: nights[0]?.night_of ?? null })
    } catch {
      return HttpResponse.json(
        { detail: 'Fila 1: el fichero no es JSON válido' },
        { status: 422 },
      )
    }
  }),

  http.put('/api/checkin', async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ day: '2026-09-06', saved: Object.keys(body) })
  }),

  http.get('/api/tips/today', ({ request }) =>
    unauthorized(request)
      ? HttpResponse.json({ detail: 'No autenticado' }, { status: 401 })
      : HttpResponse.json(mockTips),
  ),

  http.get('/api/insights', ({ request }) =>
    unauthorized(request)
      ? HttpResponse.json({ detail: 'No autenticado' }, { status: 401 })
      : HttpResponse.json(mockInsights),
  ),

  http.get('/api/dev/users', ({ request }) =>
    unauthorized(request)
      ? HttpResponse.json({ detail: 'No autenticado' }, { status: 401 })
      : HttpResponse.json(mockDevUsers),
  ),

  http.get('/api/dev/users/:userId', ({ request }) =>
    unauthorized(request)
      ? HttpResponse.json({ detail: 'No autenticado' }, { status: 401 })
      : HttpResponse.json(mockDevUserDetail),
  ),

  http.post('/api/checkin/stream', async ({ request }) => {
    const body = (await request.json()) as { message: string }
    return new HttpResponse(createCheckinSseStream(body.message), {
      headers: { 'Content-Type': 'text/event-stream' },
    })
  }),
]
