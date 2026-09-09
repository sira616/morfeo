import { Button } from '@/components/atoms/Button'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import type { SimulationParams } from '@/api/morfeo'

/**
 * El simulador: mover una señal y ver la hora reaccionar.
 *
 * Cada control empieza en «Hoy» y ese estado **no es cero**: «hoy» es «usa lo que
 * hay» y «0» es «simula que no hubo». Son la misma casilla vacía en casi cualquier
 * formulario, y aquí distinguirlas es la mitad del asunto: la pregunta más útil que
 * se le puede hacer a esto es qué pasaría en un día sin café, y sin esa diferencia no
 * hay forma de escribirla.
 *
 * Por eso los controles son fichas y no cajas de número: una ficha puede decir «Hoy»
 * y otra «0», y se ve cuál está puesta sin leer nada.
 */

type Opcion<T> = { valor: T | undefined; etiqueta: string }

function ChipRow<T extends string | number>({
  legend,
  hint,
  opciones,
  valor,
  onChange,
}: {
  legend: string
  hint?: string
  opciones: Opcion<T>[]
  valor: T | undefined
  onChange: (valor: T | undefined) => void
}) {
  return (
    <fieldset>
      <legend className="text-body-sm font-semibold">{legend}</legend>
      {hint ? <p className="mb-2 text-body-sm opacity-60">{hint}</p> : null}
      <div className="mt-2 flex flex-wrap gap-2">
        {opciones.map((opcion) => {
          const activa = opcion.valor === valor
          return (
            <button
              key={String(opcion.valor ?? 'hoy')}
              type="button"
              aria-pressed={activa}
              onClick={() => onChange(opcion.valor)}
              className="min-h-touch rounded-full px-3 py-1 text-body-sm focus-visible:outline-none focus-visible:ring-2"
              style={{
                background: activa ? 'var(--mf-primary)' : 'var(--mf-surf-2)',
                color: activa ? 'var(--mf-on-primary)' : undefined,
                border: '1px solid var(--mf-line-strong)',
              }}
            >
              {opcion.etiqueta}
            </button>
          )
        })}
      </div>
    </fieldset>
  )
}

function TimeField({
  id,
  label,
  value,
  onChange,
}: {
  id: string
  label: string
  value: string | undefined
  onChange: (value: string | undefined) => void
}) {
  return (
    <div>
      <label htmlFor={id} className="text-body-sm font-semibold">
        {label}
      </label>
      <div className="mt-2 flex gap-2">
        <input
          id={id}
          type="time"
          value={value ? value.slice(0, 5) : ''}
          onChange={(e) => onChange(e.target.value ? `${e.target.value}:00` : undefined)}
          className="min-h-touch flex-1 rounded-md px-3"
          style={{
            background: 'var(--mf-surf-2)',
            border: '1px solid var(--mf-line-strong)',
          }}
        />
        <Button variant="ghost" onClick={() => onChange(undefined)} disabled={!value}>
          Quitar
        </Button>
      </div>
    </div>
  )
}

/** Al elegir intensidad hay que decir cuánto: el motor solo cuenta la carga a partir
 *  de 45 min, así que una intensidad sin minutos no movería nada. */
const MINUTOS_DE_EJERCICIO_SIMULADO = 60

export function Simulator({
  sim,
  onChange,
  activo,
}: {
  sim: SimulationParams
  onChange: (sim: SimulationParams) => void
  activo: boolean
}) {
  function set(cambios: Partial<SimulationParams>) {
    const siguiente = { ...sim, ...cambios }
    for (const clave of Object.keys(siguiente) as (keyof SimulationParams)[]) {
      if (siguiente[clave] === undefined) delete siguiente[clave]
    }
    onChange(siguiente)
  }

  return (
    <SurfaceCard className="flex flex-col gap-5">
      <div>
        <h2 className="text-body-sm font-semibold">¿Y si el día hubiera ido de otra forma?</h2>
        <p className="mt-1 text-body-sm opacity-70">
          Cambia lo que quieras y mira cómo se mueve la hora. No toca tu perfil, no se
          guarda y no cuenta para el histórico.
        </p>
      </div>

      <TimeField
        id="sim-wake"
        label="Despertar a las"
        value={sim.wake_target}
        onChange={(wake_target) => set({ wake_target })}
      />

      <ChipRow
        legend="Cafés"
        hint="«Hoy» usa los que hayas apuntado; «0» simula un día sin café."
        valor={sim.coffees}
        opciones={[
          { valor: undefined, etiqueta: 'Hoy' },
          { valor: 0, etiqueta: 'Ninguno' },
          { valor: 1, etiqueta: '1' },
          { valor: 2, etiqueta: '2' },
          { valor: 3, etiqueta: '3' },
          { valor: 4, etiqueta: '4 o más' },
        ]}
        onChange={(coffees) =>
          set({
            coffees,
            // Sin hora, el número de cafés no mueve nada: lo que penaliza es cuándo
            // fue el último, no cuántos. Se propone media tarde y se puede cambiar.
            last_caffeine:
              coffees === undefined || coffees === 0
                ? undefined
                : (sim.last_caffeine ?? '17:00:00'),
          })
        }
      />

      {sim.coffees !== undefined && sim.coffees > 0 ? (
        <TimeField
          id="sim-caffeine"
          label="El último, a las"
          value={sim.last_caffeine}
          onChange={(last_caffeine) => set({ last_caffeine })}
        />
      ) : null}

      <ChipRow
        legend="Siesta"
        valor={sim.nap_minutes}
        opciones={[
          { valor: undefined, etiqueta: 'Hoy' },
          { valor: 0, etiqueta: 'Sin siesta' },
          { valor: 20, etiqueta: '20 min' },
          { valor: 40, etiqueta: '40 min' },
          { valor: 60, etiqueta: '1 h' },
        ]}
        onChange={(nap_minutes) => set({ nap_minutes })}
      />

      <ChipRow
        legend="Ejercicio"
        hint={`Se simula ${MINUTOS_DE_EJERCICIO_SIMULADO} min. Lo que más pesa es a qué hora acaba.`}
        valor={sim.exercise_intensity}
        opciones={[
          { valor: undefined, etiqueta: 'Hoy' },
          { valor: 'none', etiqueta: 'Nada' },
          { valor: 'light', etiqueta: 'Suave' },
          { valor: 'moderate', etiqueta: 'Moderado' },
          { valor: 'hard', etiqueta: 'Fuerte' },
        ]}
        onChange={(exercise_intensity) =>
          set({
            exercise_intensity,
            exercise_minutes:
              exercise_intensity === undefined
                ? undefined
                : exercise_intensity === 'none'
                  ? 0
                  : MINUTOS_DE_EJERCICIO_SIMULADO,
            exercise_end:
              exercise_intensity === undefined || exercise_intensity === 'none'
                ? undefined
                : (sim.exercise_end ?? '20:00:00'),
          })
        }
      />

      {sim.exercise_intensity !== undefined && sim.exercise_intensity !== 'none' ? (
        <TimeField
          id="sim-exercise-end"
          label="Terminé de entrenar a las"
          value={sim.exercise_end}
          onChange={(exercise_end) => set({ exercise_end })}
        />
      ) : null}

      {activo ? (
        <Button variant="secondary" onClick={() => onChange({})}>
          Volver a mi día real
        </Button>
      ) : null}
    </SurfaceCard>
  )
}
