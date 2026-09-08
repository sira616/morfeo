import type { AuthUser } from '@/stores/authStore'
import type { Night, Recommendation } from '@/api/morfeo'

export const mockUser: AuthUser = {
  id: 'user-demo',
  email: 'demo@morfeo.app',
  displayName: 'Demo',
  onboardingDone: true,
  defaultWakeTime: '07:00:00',
  sleepNeedMinutes: 480,
  declaredLatencyMinutes: 25,
  wearableProvider: 'import',
}

/**
 * Una racha de eficiencia baja a propósito: es el caso interesante, el que dispara el
 * modo restricción, y el que hay que poder ver sin esperar dos semanas de datos reales.
 */
export const mockNights: Night[] = Array.from({ length: 21 }, (_, i) => {
  const day = new Date('2026-09-06')
  day.setDate(day.getDate() - i)
  const slept = 360 + ((i * 37) % 60)
  const inBed = slept + 90 + ((i * 13) % 40)
  return {
    night_of: day.toISOString().slice(0, 10),
    total_sleep_minutes: slept,
    time_in_bed_minutes: inBed,
    onset_latency_minutes: 30 + ((i * 7) % 20),
    efficiency: Number((slept / inBed).toFixed(3)),
    source: 'import',
  }
})

export const mockRecommendation: Recommendation = {
  day: '2026-09-06',
  wake_target: '07:00:00',
  bedtime: '23:35:00',
  window_start: '23:15:00',
  window_end: '23:55:00',
  target_sleep_minutes: 540,
  time_in_bed_minutes: 415,
  onset_latency_minutes: 30,
  mode: 'restriccion',
  confidence: 'alta',
  factors: [
    { label: 'Necesidad basal', minutes: 480, detail: 'Tu necesidad de sueño de referencia' },
    {
      label: 'Deuda de sueño',
      minutes: 60,
      detail: 'Arrastras 840 min de déficit; se recupera a plazos, no en una sola noche',
    },
  ],
  notes: [
    'Tu eficiencia de sueño es del 78% (dormido frente a tiempo en la cama). Por debajo del 85% lo indicado es acortar la ventana, no alargarla: pasar horas despierta en la cama entrena al cerebro a no dormir en ella.',
  ],
  followed: null,
}
