import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import { NightLogForm } from '@/components/night/NightLogForm'
import { routes } from '@/router/paths'

/**
 * El paso siguiente a marcar si seguiste la recomendación.
 *
 * Marcarlo sin más solo dice si te acostaste a la hora; lo que cierra el bucle de
 * verdad es qué pasó después. Sin reloj conectado, esta pantalla es la única forma de
 * que el motor conozca tu latencia y tu eficiencia reales.
 */
export function NightLogPage() {
  const navigate = useNavigate()

  return (
    // Una sola tarea y un solo formulario: centrado y con tope, que es lo que ayuda a
    // rellenarlo de una sentada. Solo se le quita el estrangulamiento a 672 px.
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <Link to={routes.tonight} className="flex items-center gap-2 text-body-sm underline">
        <ArrowLeft aria-hidden size={16} />
        Volver
      </Link>

      <NightLogForm onSaved={() => navigate(routes.tonight)} />

      <p className="px-2 text-body-sm opacity-60">
        Si conectas un reloj, esto deja de hacer falta: los mismos datos llegan solos
        desde «Reloj».
      </p>
    </div>
  )
}
