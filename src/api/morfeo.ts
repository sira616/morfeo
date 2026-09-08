import { apiClient } from '@/lib/apiClient'

export type Factor = {
  label: string
  minutes: number
  detail: string
}

export type Recommendation = {
  day: string
  wake_target: string
  bedtime: string
  window_start: string
  window_end: string
  target_sleep_minutes: number
  time_in_bed_minutes: number
  onset_latency_minutes: number
  mode: 'normal' | 'restriccion'
  confidence: 'baja' | 'media' | 'alta'
  factors: Factor[]
  notes: string[]
  followed: boolean | null
}

export type Night = {
  night_of: string
  total_sleep_minutes: number
  time_in_bed_minutes: number
  onset_latency_minutes: number | null
  efficiency: number
  source: string
}

export type CheckinFields = {
  mood?: number
  energy?: number
  perceived_stress?: number
  nap_minutes?: number
  last_caffeine?: string | null
  alcohol?: boolean
  wake_target?: string | null
}

/** `wakeTarget` simula otra hora de despertar sin tocar el perfil ni guardar nada. */
export function getTonight(wakeTarget?: string) {
  const query = wakeTarget ? `?wake_target=${encodeURIComponent(wakeTarget)}` : ''
  return apiClient<Recommendation>(`/api/bedtime/tonight${query}`)
}

export function getRecommendationHistory(limit = 30) {
  return apiClient<Recommendation[]>(`/api/bedtime/history?limit=${limit}`)
}

export function markFollowed(day: string, followed: boolean) {
  return apiClient<void>(`/api/bedtime/${day}/followed`, {
    method: 'PATCH',
    body: { followed },
  })
}

export function getNights(days = 30) {
  return apiClient<Night[]>(`/api/sleep/nights?days=${days}`)
}

export function saveCheckin(fields: CheckinFields) {
  return apiClient<{ day: string; saved: string[] }>('/api/checkin', {
    method: 'PUT',
    body: fields,
  })
}

/** Importa la exportación de un reloj. El backend responde 422 con la fila que falla. */
export function importNights(content: string, format: 'json' | 'csv') {
  return apiClient<{ written: number; from: string | null }>('/api/sleep/import', {
    method: 'POST',
    body: { content, format },
  })
}
