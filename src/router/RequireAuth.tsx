import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { routes } from '@/router/paths'

/**
 * UI session guard only. API authorization is enforced by the mock/backend.
 */
export function RequireAuth() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const restoring = useAuthStore((s) => s.restoring)
  const location = useLocation()

  // Sin esta espera, recargar una ruta protegida rebota al login antes de que dé
  // tiempo a canjear el refresh guardado, y la sesión parece perdida igualmente.
  if (restoring) {
    return <p className="py-8 text-center opacity-70">Un momento…</p>
  }

  if (!accessToken) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`${routes.login}?next=${next}`} replace />
  }

  return <Outlet />
}
