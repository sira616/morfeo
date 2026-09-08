import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ShieldCheck } from 'lucide-react'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { getDevUser, getDevUsers, type DevUser } from '@/api/morfeo'
import { routes } from '@/router/paths'

const ACTION_LABELS: Record<string, string> = {
  login: 'Inicio de sesión',
  checkin: 'Check-in',
  nights: 'Alta de noches',
  import: 'Importación',
  metrics: 'Métricas del día',
  followed: 'Marcó la recomendación',
  profile: 'Cambio de perfil',
}

function when(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  return date.toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })
}

function onlyDate(value: string | null): string {
  return value ? value.slice(0, 10) : '—'
}

/**
 * Panel de administración.
 *
 * La puerta de verdad está en el backend, que responde 404 a quien no es admin. Esto
 * es conveniencia de interfaz: sin la ruta oculta seguiría sin poder ver nada, pero
 * enseñar un enlace roto a quien no puede entrar es peor que no enseñarlo.
 */
export function DevPage() {
  const { data: users, isLoading, isError } = useQuery({
    queryKey: ['dev-users'],
    queryFn: getDevUsers,
  })

  if (isLoading) return <p className="py-8 text-center opacity-70">Cargando…</p>
  if (isError || !users) {
    return (
      <SurfaceCard className="text-center">
        <p>No se pudo cargar el panel.</p>
        <p className="mt-1 text-body-sm opacity-70">
          Solo las cuentas de <code>ADMIN_EMAILS</code> tienen acceso.
        </p>
      </SurfaceCard>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-6 lg:grid-cols-3">
        <Stat label="Perfiles" value={String(users.length)} />
        <Stat
          label="Con onboarding hecho"
          value={String(users.filter((u) => u.onboarding_done).length)}
        />
        <Stat
          label="Con noches registradas"
          value={String(users.filter((u) => u.nights > 0).length)}
        />
      </div>

      <SurfaceCard padded={false}>
        <table className="w-full text-body-sm">
          <caption className="sr-only">Perfiles registrados</caption>
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--mf-line)' }}>
              <th scope="col" className="p-3 text-left">Cuenta</th>
              <th scope="col" className="p-3 text-right">Noches</th>
              <th scope="col" className="p-3 text-right">Check-ins</th>
              <th scope="col" className="p-3 text-right">Última actividad</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b" style={{ borderColor: 'var(--mf-line)' }}>
                <th scope="row" className="p-3 text-left font-normal">
                  <Link to={routes.devUser(user.id)} className="underline">
                    {user.email}
                  </Link>
                  {user.is_admin ? (
                    <ShieldCheck
                      aria-label="Administrador"
                      size={14}
                      className="ml-1 inline"
                      style={{ color: 'var(--mf-good)' }}
                    />
                  ) : null}
                </th>
                <td className="p-3 text-right tabular-nums">{user.nights}</td>
                <td className="p-3 text-right tabular-nums">{user.checkins}</td>
                <td className="p-3 text-right tabular-nums">{when(user.last_seen)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </SurfaceCard>

      <p className="px-2 text-[11px] opacity-50">
        El registro guarda qué acción hizo cada persona y qué campos tocó, nunca lo que
        escribió. Los check-ins y las conversaciones no se pueden leer desde aquí.
      </p>
    </div>
  )
}

export function DevUserPage() {
  const { userId = '' } = useParams()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dev-user', userId],
    queryFn: () => getDevUser(userId),
  })

  if (isLoading) return <p className="py-8 text-center opacity-70">Cargando…</p>
  if (isError || !data) {
    return <SurfaceCard className="text-center">No se encontró ese perfil.</SurfaceCard>
  }

  const { user, activity, events } = data

  return (
    <div className="flex flex-col gap-6">
      <Link to={routes.dev} className="flex items-center gap-2 text-body-sm underline">
        <ArrowLeft aria-hidden size={16} />
        Volver a los perfiles
      </Link>

      <SurfaceCard>
        <h2 className="text-headline-sm font-bold">{user.email}</h2>
        <dl className="mt-3 grid grid-cols-2 gap-3 text-body-sm sm:grid-cols-4">
          <Detail label="Alta" value={onlyDate(user.created_at)} />
          <Detail label="Noches" value={String(user.nights)} />
          <Detail label="Check-ins" value={String(user.checkins)} />
          <Detail label="Recomendaciones" value={String(user.recommendations)} />
          <Detail label="Última noche" value={onlyDate(user.last_night)} />
          <Detail label="Reloj" value={user.wearable_provider ?? '—'} />
          <Detail label="Onboarding" value={user.onboarding_done ? 'Hecho' : 'Pendiente'} />
          <Detail label="Admin" value={user.is_admin ? 'Sí' : 'No'} />
        </dl>
      </SurfaceCard>

      <div className="grid gap-6 lg:grid-cols-[18rem_1fr]">
        <SurfaceCard>
          <h3 className="mb-2 text-body-sm font-bold">Últimos 30 días</h3>
          {activity.length === 0 ? (
            <p className="text-body-sm opacity-70">Sin actividad.</p>
          ) : (
            <ul className="flex flex-col gap-2 text-body-sm">
              {activity.map((a) => (
                <li key={a.action} className="flex justify-between gap-3">
                  <span>{ACTION_LABELS[a.action] ?? a.action}</span>
                  <span className="tabular-nums opacity-70">{a.count}</span>
                </li>
              ))}
            </ul>
          )}
        </SurfaceCard>

        <SurfaceCard padded={false}>
          <table className="w-full text-body-sm">
            <caption className="sr-only">Registro de actividad</caption>
            <thead>
              <tr className="border-b" style={{ borderColor: 'var(--mf-line)' }}>
                <th scope="col" className="p-3 text-left">Cuándo</th>
                <th scope="col" className="p-3 text-left">Qué</th>
                <th scope="col" className="p-3 text-left">Detalle</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event, index) => (
                <tr
                  key={`${event.at}-${index}`}
                  className="border-b"
                  style={{ borderColor: 'var(--mf-line)' }}
                >
                  <td className="p-3 tabular-nums whitespace-nowrap">{when(event.at)}</td>
                  <td className="p-3">{ACTION_LABELS[event.action] ?? event.action}</td>
                  <td className="p-3 opacity-70">{event.summary ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {events.length === 0 ? (
            <p className="p-3 text-body-sm opacity-70">Sin eventos registrados.</p>
          ) : null}
        </SurfaceCard>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <SurfaceCard>
      <p className="text-body-sm opacity-60">{label}</p>
      <p className="text-display-md font-bold tabular-nums">{value}</p>
    </SurfaceCard>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="opacity-60">{label}</dt>
      <dd className="font-bold">{value}</dd>
    </div>
  )
}

export type { DevUser }
