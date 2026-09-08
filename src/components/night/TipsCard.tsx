import { useQuery } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { getTips, type Tip } from '@/api/morfeo'

const EVIDENCE_LABEL: Record<Tip['evidence'], string> = {
  alta: 'Evidencia alta',
  media: 'Evidencia media',
  baja: 'Evidencia limitada',
}

/**
 * El nivel de evidencia se enseña, y es lo que separa esto de una lista de tópicos.
 * La Academia Americana de Medicina del Sueño recomienda no usar la higiene del sueño
 * como tratamiento único del insomnio; presentar "ventila la habitación" con el mismo
 * peso que "reserva la cama para dormir" sería mentir por omisión.
 */
function EvidenceBadge({ evidence }: { evidence: Tip['evidence'] }) {
  const strong = evidence === 'alta'
  return (
    <span
      className="shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold"
      style={
        strong
          ? { background: 'var(--mf-good-tint)', color: 'var(--mf-good)' }
          : { background: 'var(--mf-surf-3)', color: 'var(--mf-ink-dim)' }
      }
    >
      {EVIDENCE_LABEL[evidence]}
    </span>
  )
}

export function TipsCard() {
  const { data, isLoading, isError } = useQuery({ queryKey: ['tips'], queryFn: getTips })

  return (
    <SurfaceCard>
      <h2 className="mb-1 flex items-center gap-2 text-headline-sm font-bold">
        <Sparkles aria-hidden size={18} style={{ color: 'var(--mf-good)' }} />
        Cinco cosas que ayudan
      </h2>
      <p className="mb-4 text-body-sm opacity-70">
        Cambian cada día. Los marcados salen por algo que te pasa hoy.
      </p>

      {isLoading ? <p className="text-body-sm opacity-70">Cargando…</p> : null}
      {isError ? (
        <p className="text-body-sm opacity-70">No se pudieron cargar los consejos.</p>
      ) : null}

      <ul className="flex flex-col gap-4">
        {data?.tips.map((tip) => (
          <li
            key={tip.id}
            className="border-l-2 pl-3"
            style={{
              borderColor: tip.relevant ? 'var(--mf-good)' : 'var(--mf-line)',
            }}
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-body-sm font-bold">{tip.title}</h3>
              <EvidenceBadge evidence={tip.evidence} />
            </div>
            <p className="mt-1 text-body-sm opacity-80">{tip.body}</p>
            <p className="mt-1 text-[11px] opacity-50">{tip.source}</p>
          </li>
        ))}
      </ul>

      <p className="mt-4 text-[11px] opacity-50">
        Hábitos, no tratamiento. Los consejos por sí solos no curan el insomnio: lo que
        funciona es la parte conductual que Morfeo ya calcula.
      </p>
    </SurfaceCard>
  )
}
