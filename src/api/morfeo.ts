import { apiClient } from '@/lib/apiClient'

export type Factor = {
  label: string
  minutes: number
  detail: string
}

export type Recommendation = {
  day: string
  wake_target: string
  /** De dónde sale la hora de despertar: el perfil, el check-in de hoy o el simulador. */
  wake_target_source: 'perfil' | 'checkin' | 'simulacion'
  bedtime: string
  window_start: string
  window_end: string
  target_sleep_minutes: number
  /** Desde que te duermes hasta el despertador; **sin** la conciliación. */
  sleep_window_minutes: number
  /** Lo que de verdad pasas en la cama: lo anterior más la conciliación. */
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
  /** Falta cuando la exportación del reloj solo trajo duraciones. */
  bed_at: string | null
  efficiency: number
  source: string
}

export type Intensity = 'none' | 'light' | 'moderate' | 'hard'

export type CheckinFields = {
  mood?: number
  energy?: number
  perceived_stress?: number
  nap_minutes?: number
  last_caffeine?: string | null
  alcohol?: boolean
  wake_target?: string | null
  coffees?: number
  alcohol_units?: number
  /** Días desde el último porro. 0 = hoy; null = no aplica. */
  cannabis_days_ago?: number | null
  exercise_minutes?: number
  exercise_intensity?: Intensity
  exercise_end?: string | null
  meals?: number | null
  last_meal?: string | null
  notes?: string | null
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

export type NightIn = {
  night_of: string
  total_sleep_minutes: number
  time_in_bed_minutes: number
  onset_latency_minutes?: number
  awakenings?: number
  bed_at?: string
}

/** Alta manual de una noche. Idempotente por fecha: reenviarla la corrige. */
export function saveNight(night: NightIn) {
  return apiClient<{ written: number }>('/api/sleep/nights', {
    method: 'POST',
    body: { nights: [night] },
  })
}

export type RecentCheckin = {
  day: string
  mood: number | null
  energy: number | null
  nap_minutes: number
  coffees: number
  alcohol_units: number
  cannabis_days_ago: number | null
}

export function getRecentCheckins(days = 14) {
  return apiClient<RecentCheckin[]>(`/api/checkin/recent?days=${days}`)
}

export function getNights(days = 30) {
  return apiClient<Night[]>(`/api/sleep/nights?days=${days}`)
}

/** Quita la hora de despertar del check-in de hoy para que vuelva a mandar el perfil. */
export function clearCheckinWakeTarget() {
  return apiClient<{ day: string; saved: string[] }>('/api/checkin', {
    method: 'PUT',
    body: { wake_target: null },
  })
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

export type Association = {
  key: string
  label: string
  nights_with: number
  nights_without: number
  mean_sleep_with: number
  mean_sleep_without: number
  mean_efficiency_with: number
  mean_efficiency_without: number
  delta_sleep_minutes: number
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
  /** Vacío mientras no haya check-ins suficientes a los dos lados de cada factor. */
  associations: Association[]
  adherence: { streak: number; rate: number | null; series: AdherenceNight[] }
  heatmap: HeatmapNight[]
}

export function getTips() {
  return apiClient<TipsToday>('/api/tips/today')
}

export function getInsights() {
  return apiClient<Insights>('/api/insights')
}

// --- Panel de /dev -----------------------------------------------------------
// Solo devuelve qué registró cada persona y cuándo, nunca lo que escribió.

export type DevUser = {
  id: string
  username: string
  email: string | null
  display_name: string | null
  is_admin: boolean
  onboarding_done: boolean
  created_at: string | null
  wearable_provider: string | null
  nights: number
  checkins: number
  recommendations: number
  last_night: string | null
  last_seen: string | null
}

export type DevEvent = {
  at: string
  action: string
  summary: string | null
}

export type DevUserDetail = {
  user: DevUser
  activity: { action: string; count: number; last: string | null }[]
  events: DevEvent[]
}

export function getDevUsers() {
  return apiClient<DevUser[]>('/api/dev/users')
}

export function getDevUser(userId: string) {
  return apiClient<DevUserDetail>(`/api/dev/users/${userId}`)
}
