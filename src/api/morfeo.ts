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

export type Tip = {
  id: string
  title: string
  body: string
  category: string
  evidence: 'alta' | 'media' | 'baja'
  source: string
  /** True cuando sale por algo que pasa hoy, no por relleno. */
  relevant: boolean
}

export type TipsToday = {
  day: string
  signals: string[]
  tips: Tip[]
}

export type Regularity = {
  score: number
  sd_minutes: number
  mean_midpoint_minutes: number
  nights: number
}

export type SocialJetlag = {
  minutes: number
  weekday_midpoint_minutes: number
  weekend_midpoint_minutes: number
  weekday_nights: number
  weekend_nights: number
}

export type AdherenceNight = {
  day: string
  recommended: string
  /** Falta cuando el reloj no trajo la hora real de acostarse. */
  actual: string | null
  followed: boolean | null
}

export type HeatmapNight = {
  night_of: string
  total_sleep_minutes: number
  efficiency: number
}

export type Insights = {
  /** Null, no cero: sin noches suficientes no hay métrica que enseñar. */
  regularity: Regularity | null
  social_jetlag: SocialJetlag | null
  adherence: { streak: number; rate: number | null; series: AdherenceNight[] }
  heatmap: HeatmapNight[]
}

export function getTips() {
  return apiClient<TipsToday>('/api/tips/today')
}

export function getInsights() {
  return apiClient<Insights>('/api/insights')
}
