import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { routes } from '@/router/paths'

/**
 * UI session guard only. API authorization is enforced by the mock/backend.
 */
export function RequireAuth() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const location = useLocation()

  if (!accessToken) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`${routes.login}?next=${next}`} replace />
  }

  return <Outlet />
}
