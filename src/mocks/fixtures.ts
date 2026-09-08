import type { AuthUser } from '@/stores/authStore'
import type { AdherenceNight, Insights, Night, Recommendation, TipsToday } from '@/api/morfeo'

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

/** Fechas relativas a hoy: si fueran fijas, el heatmap se saldría de la ventana. */
function daysAgo(days: number): string {
  const date = new Date()
  date.setDate(date.getDate() - days)
  return date.toISOString().slice(0, 10)
}

const MOCK_NIGHT_COUNT = 42

/**
 * Seis semanas de noches, **de la más antigua a la más reciente**, igual que las
 * devuelve el backend. Si el mock las diera al revés, la tabla y la gráfica se leerían
 * invertidas en desarrollo y nadie lo notaría hasta conectar la API real.
 *
 * La eficiencia mejora poco a poco, de un 70% a un 86%: la media se queda por debajo
 * del 85% (que es lo que dispara el modo restricción, el caso interesante) pero hay
 * noches buenas, así que la leyenda del heatmap enseña sus dos colores.
 */
export const mockNights: Night[] = Array.from({ length: MOCK_NIGHT_COUNT }, (_, i) => {
  const progress = i / (MOCK_NIGHT_COUNT - 1)
  const wobble = ((i * 37) % 40) - 20
  const slept = Math.round(345 + progress * 75 + wobble)
  const inBed = Math.round(slept / (0.7 + progress * 0.16))
  return {
    night_of: daysAgo(MOCK_NIGHT_COUNT - i),
    total_sleep_minutes: slept,
    time_in_bed_minutes: inBed,
    onset_latency_minutes: 30 + ((i * 7) % 20),
    efficiency: Number((slept / inBed).toFixed(3)),
    source: 'import',
  }
})

export const mockRecommendation: Recommendation = {
  day: daysAgo(0),
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

const mockAdherence: AdherenceNight[] = Array.from({ length: 14 }, (_, i) => {
  const drift = ((i * 17) % 50) - 20
  const base = 23 * 60 + 35 + drift
  return {
    day: daysAgo(14 - i),
    recommended: '23:35:00',
    actual: i % 5 === 3 ? null : `${String(Math.floor(base / 60) % 24).padStart(2, '0')}:${String(base % 60).padStart(2, '0')}:00`,
    followed: i % 5 === 3 ? null : drift < 20,
  }
})

export const mockInsights: Insights = {
  regularity: {
    score: 62,
    sd_minutes: 46,
    mean_midpoint_minutes: 3 * 60 + 20,
    nights: 21,
  },
  social_jetlag: {
    minutes: 74,
    weekday_midpoint_minutes: 3 * 60 + 5,
    weekend_midpoint_minutes: 4 * 60 + 19,
    weekday_nights: 15,
    weekend_nights: 6,
  },
  adherence: {
    streak: 3,
    rate: 0.64,
    series: mockAdherence,
  },
  heatmap: mockNights.map((n) => ({
    night_of: n.night_of,
    total_sleep_minutes: n.total_sleep_minutes,
    efficiency: n.efficiency,
  })),
}

export const mockTips: TipsToday = {
  day: daysAgo(0),
  signals: ['cafeina_tarde', 'eficiencia_baja'],
  tips: [
    {
      id: 'cafeina-vida-media',
      title: 'La cafeína dura más de lo que parece',
      body: 'Su vida media son 3 a 6 horas, pero varía muchísimo: hay quien la elimina en 2 y quien tarda 10. En un ensayo de 2024, 400 mg alteraron la arquitectura del sueño incluso tomados 12 horas antes.',
      category: 'sustancias',
      evidence: 'alta',
      source: 'Gardiner et al., SLEEP 2024 (ensayo cruzado aleatorizado)',
      relevant: true,
    },
    {
      id: 'cama-solo-dormir',
      title: 'La cama, para dormir',
      body: 'Trabajar, ver series o dar vueltas a las cosas en la cama enseña al cerebro que ese sitio es para estar despierta. Deshacer esa asociación es la mitad del trabajo en el insomnio de inicio.',
      category: 'cama',
      evidence: 'alta',
      source: 'Control de estímulos, componente central de la TCC-I',
      relevant: true,
    },
    {
      id: 'actividad-ducha',
      title: 'Ducha caliente una o dos horas antes',
      body: 'De todo lo que puedes hacer, es lo que más rinde por el esfuerzo que cuesta: diez minutos bastan y acortan lo que tardas en dormirte alrededor de un 36%.',
      category: 'actividad',
      evidence: 'alta',
      source: 'Haghayegh et al., Sleep Medicine Reviews 2019 (metaanálisis, 13 ensayos)',
      relevant: false,
    },
    {
      id: 'luz-gafas-azules',
      title: 'Las gafas de luz azul están sobrevaloradas',
      body: 'La revisión Cochrane de 2023 no encontró evidencia convincente de que mejoren el sueño. Baja el brillo y la luz de la habitación: eso sí pesa.',
      category: 'luz',
      evidence: 'alta',
      source: 'Revisión Cochrane 2023 sobre lentes que filtran luz azul',
      relevant: false,
    },
    {
      id: 'entorno-temperatura',
      title: 'Mejor fresco que templado',
      body: 'Para dormir, el cuerpo necesita bajar su temperatura central un grado o dos. Entre 18 y 21 °C es el rango que suele recomendarse; por encima, la eficiencia del sueño cae de forma medible.',
      category: 'entorno',
      evidence: 'media',
      source: 'Estudios de temperatura ambiente y eficiencia del sueño',
      relevant: false,
    },
  ],
}
