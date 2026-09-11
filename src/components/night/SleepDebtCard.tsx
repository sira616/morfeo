import { TrendingDown, TrendingUp } from 'lucide-react'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import type { SleepDebt } from '@/api/morfeo'

/**
 * La deuda de sueño de la portada.
 *
 * La regla que ordena todo lo demás: **el plazo va pegado a la cifra**. Un número de
 * deuda creciendo, solo y de noche, es ansiedad y no información, y esta tarjeta se
 * mira justo antes de dormir. Por eso `nights_to_clear` no está detrás de un
 * desplegable ni al final de la tarjeta: va en la frase siguiente a los minutos, y no
 * hay ningún estado en el que se enseñe la deuda sin él.
 *
 * De ahí salen las otras dos decisiones:
 *
 * - **La cifra grande no lleva color.** El nivel sí, en una palabra pequeña al lado.
 *   Veintiséis horas en rojo a las once de la noche no informan de nada que la palabra
 *   «alta» no diga ya, y de noche el rojo se lee como una alarma que no se puede
 *   atender hasta mañana.
 * - **Cero noches no es cero deuda.** Una cuenta recién creada devuelve `minutes: 0`
 *   con `nights_counted: 0`; pintarlo como «sin deuda» sería felicitar a alguien por
 *   un dato que nadie ha medido. Es la misma regla que el backend aplica devolviendo
 *   `null` en vez de cero en el resto de métricas.
 */

function horas(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m} min`
  if (m === 0) return `${h} h`
  return `${h} h ${String(m).padStart(2, '0')}`
}

function noches(n: number): string {
  return n === 1 ? '1 noche' : `${n} noches`
}

const COLOR_NIVEL: Record<SleepDebt['level'], string> = {
  ninguna: 'var(--mf-good)',
  leve: 'var(--mf-good)',
  moderada: 'var(--mf-chart-awake)',
  alta: 'var(--mf-chart-awake)',
}

export function SleepDebtCard({ debt }: { debt: SleepDebt | null }) {
  // El histórico no la trae: la deuda no se congeló con cada recomendación.
  if (!debt) return null

  // Sin noches medidas no hay nada que decir, y decir "sin deuda" sería inventárselo.
  if (debt.nights_counted === 0) {
    return (
      <SurfaceCard>
        <h2 className="text-headline-sm font-bold">Deuda de sueño</h2>
        <p className="mt-2 text-body-sm opacity-70">
          Aparecerá en cuanto haya noches con horas reales. Se calcula sobre las últimas
          catorce, así que necesita unos días de registro; puedes darle de comer desde
          «Reloj» o apuntando cómo fue anoche.
        </p>
      </SurfaceCard>
    )
  }

  const saldada = debt.minutes === 0

  return (
    <SurfaceCard>
      <h2 className="text-headline-sm font-bold">Deuda de sueño</h2>
      <p className="mb-3 text-body-sm opacity-70">
        El déficit de las últimas {noches(debt.nights_counted)}.
      </p>

      {saldada ? (
        <p className="text-headline-sm font-bold" style={{ color: 'var(--mf-good)' }}>
          Al día. No arrastras déficit.
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-display-md font-bold tabular-nums">
              {horas(debt.minutes)}
            </span>
            <span
              className="text-body-sm font-semibold uppercase tracking-wide"
              style={{ color: COLOR_NIVEL[debt.level] }}
            >
              {debt.level}
            </span>
          </div>

          {/* Lo importante de toda la tarjeta. Va aquí y no más abajo: la cifra de
              arriba sin esta frase es el número que no conviene enseñar de noche. */}
          <p className="mt-1 text-body-sm">
            Se salda en unas <strong>{noches(debt.nights_to_clear)}</strong> durmiendo lo
            que necesitas. No hace falta recuperarla de golpe.
          </p>
        </>
      )}

      <dl className="mt-4 grid grid-cols-2 gap-3 text-body-sm">
        {debt.tonight_recovery_minutes > 0 ? (
          <div>
            <dt className="opacity-60">Esta noche recupera</dt>
            <dd className="font-bold tabular-nums">+{debt.tonight_recovery_minutes} min</dd>
          </div>
        ) : null}
        {debt.nights_with_deficit > 0 ? (
          <div>
            <dt className="opacity-60">Noches por debajo</dt>
            <dd className="font-bold tabular-nums">
              {debt.nights_with_deficit} de {debt.nights_counted}
            </dd>
          </div>
        ) : null}
      </dl>

      <Tendencia delta={debt.delta_minutes} />

      <p className="mt-4 text-[11px] opacity-50">
        Se recupera un 25% por noche, con tope de una hora: dormir muchas horas de más
        una noche desplaza el ritmo circadiano y empeora la siguiente. Como la ventana
        es de catorce noches, la deuda también se salda sola según las noches malas van
        saliendo de ella.
      </p>
    </SurfaceCard>
  )
}

/**
 * La comparación con la semana pasada.
 *
 * Llega a `null` mientras la ventana de atrás no esté igual de llena. Sin esa guarda,
 * las tres primeras semanas de uso dirían «subiendo» siempre, contra un cero que nadie
 * midió: exactamente el número que no conviene enseñar de noche.
 */
function Tendencia({ delta }: { delta: number | null }) {
  if (delta === null || delta === 0) return null

  const bajando = delta < 0
  const Icono = bajando ? TrendingDown : TrendingUp
  const color = bajando ? 'var(--mf-good)' : 'var(--mf-chart-awake)'

  return (
    <p className="mt-3 flex items-center gap-2 text-body-sm">
      <Icono aria-hidden size={16} style={{ color }} />
      <span>
        <strong className="tabular-nums" style={{ color }}>
          {horas(Math.abs(delta))}
        </strong>{' '}
        {bajando ? 'menos' : 'más'} que hace una semana
      </span>
    </p>
  )
}
