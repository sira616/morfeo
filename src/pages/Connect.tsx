import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/atoms/Button'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { importNights } from '@/api/morfeo'
import { NightLogForm } from '@/components/night/NightLogForm'
import { ApiError } from '@/lib/apiClient'

const EJEMPLO = `[
  {
    "night_of": "2026-09-05",
    "total_sleep_minutes": 412,
    "time_in_bed_minutes": 470,
    "onset_latency_minutes": 35
  }
]`

/**
 * Primero apuntar la noche a mano, después conectar un reloj.
 *
 * El orden importa: sin reloj, el formulario es la **única** forma de que el motor
 * conozca tu latencia y tu eficiencia reales, y es lo que la mayoría va a usar a
 * diario. Poner primero la importación dejaba lo imprescindible debajo de lo opcional.
 */
export function ConnectPage() {
  const queryClient = useQueryClient()
  const [content, setContent] = useState('')
  const [format, setFormat] = useState<'json' | 'csv'>('json')

  const load = useMutation({
    mutationFn: () => importNights(content, format),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nights'] })
      queryClient.invalidateQueries({ queryKey: ['tonight'] })
      setContent('')
    },
  })

  async function onFile(file: File) {
    setFormat(file.name.toLowerCase().endsWith('.csv') ? 'csv' : 'json')
    setContent(await file.text())
  }

  return (
    // Dos columnas en escritorio, y el orden se mantiene en la lectura de izquierda a
    // derecha: a la izquierda lo imprescindible —apuntar la noche a mano, que sin reloj
    // es la única forma de que el motor conozca tu latencia y tu eficiencia—, a la
    // derecha lo opcional del reloj. En móvil se apila, con lo imprescindible primero.
    // Antes era una sola columna estrecha que en un monitor se veía como una app de
    // móvil pegada en medio.
    <div className="mx-auto grid w-full max-w-6xl items-start gap-6 lg:grid-cols-2">
      <div className="flex flex-col gap-4">
        <NightLogForm />
        <p className="px-2 text-body-sm opacity-60">
          Esto es lo único que hace falta a diario. Si conectas un reloj (columna de al
          lado), los mismos datos llegan solos cada mañana y puedes olvidarte.
        </p>
      </div>

      <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-headline-sm font-bold">¿Tienes un reloj?</h2>
        <p className="text-body-sm opacity-70">
          Si lo conectas, lo de al lado deja de hacer falta: los mismos datos llegan
          solos cada mañana.
        </p>
      </div>

      <SurfaceCard>
        <h2 className="mb-2 text-headline-sm font-bold">Importar del reloj</h2>
        <p className="text-body-sm opacity-80">
          Garmin, Fitbit, Samsung Health, Apple Salud y Withings dejan descargar tu
          histórico. Suelta aquí ese fichero y Morfeo se queda con las noches.
        </p>

        <input
          type="file"
          accept=".json,.csv,application/json,text/csv"
          className="mt-3 w-full text-body-sm"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void onFile(file)
          }}
        />

        <label htmlFor="paste" className="mt-4 block text-body-sm font-semibold">
          O pega el contenido
        </label>
        <textarea
          id="paste"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={8}
          spellCheck={false}
          placeholder={EJEMPLO}
          className="mt-1 w-full rounded-md p-3 font-mono text-xs"
          style={{ background: 'var(--mf-surf-2)', border: '1px solid var(--mf-line-strong)' }}
        />

        <div className="mt-2 flex items-center gap-2">
          <Button
            variant={format === 'json' ? 'primary' : 'ghost'}
            onClick={() => setFormat('json')}
          >
            JSON
          </Button>
          <Button variant={format === 'csv' ? 'primary' : 'ghost'} onClick={() => setFormat('csv')}>
            CSV
          </Button>
          <Button
            className="ml-auto"
            onClick={() => load.mutate()}
            disabled={!content.trim() || load.isPending}
          >
            {load.isPending ? 'Importando…' : 'Importar'}
          </Button>
        </div>

        {load.isSuccess ? (
          <p role="status" className="mt-3 text-body-sm">
            Importadas {load.data.written} noches.
          </p>
        ) : null}
        {load.isError ? (
          <p role="alert" className="mt-3 text-body-sm text-error">
            {load.error instanceof ApiError
              ? load.error.message
              : 'No se pudo importar el fichero.'}
          </p>
        ) : null}
      </SurfaceCard>

      <SurfaceCard>
        <h2 className="mb-2 text-headline-sm font-bold">Columnas que espera</h2>
        <p className="text-body-sm opacity-80">
          Obligatorias: <code>night_of</code> (AAAA-MM-DD), <code>total_sleep_minutes</code> y{' '}
          <code>time_in_bed_minutes</code>.
        </p>
        <p className="mt-2 text-body-sm opacity-80">
          Opcionales, pero valiosas: <code>onset_latency_minutes</code> (lo que tardas en
          dormirte, que es justo lo que la app usa para separar la hora de acostarse de la
          de dormirse), <code>awakenings</code>, <code>deep_minutes</code>,{' '}
          <code>rem_minutes</code>, <code>resting_hr</code>.
        </p>
        <pre
          className="mt-3 overflow-x-auto rounded-md p-3 text-xs"
          style={{ background: 'var(--mf-surf-2)' }}
        >
          {EJEMPLO}
        </pre>
      </SurfaceCard>

      <SurfaceCard>
        <h2 className="mb-2 text-headline-sm font-bold">Conexión automática</h2>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-body-sm opacity-80">
          <li>
            <strong>Oura</strong>: listo en el backend. Basta un Personal Access Token de tu
            panel de Oura, sin OAuth ni aprobaciones.
          </li>
          <li>
            <strong>Fitbit</strong>: pendiente. Necesita OAuth2 con PKCE y una cuenta de
            desarrollador gratuita.
          </li>
          <li>
            <strong>Garmin</strong>: su Health API exige aprobación como socio. Hasta
            entonces, exporta desde Garmin Connect e impórtalo aquí.
          </li>
        </ul>
      </SurfaceCard>
      </div>
    </div>
  )
}
