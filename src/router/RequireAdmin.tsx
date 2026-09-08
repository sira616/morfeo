import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { routes } from '@/router/paths'

/**
 * Guarda de interfaz, no de seguridad.
 *
 * Quien no es administrador recibe un 404 del backend en cada ruta de `/api/dev`,
 * aunque llegue a pintar la pantalla. Esto solo evita enseñar un panel vacío.
 */
export function RequireAdmin() {
  const user = useAuthStore((s) => s.user)
  if (!user?.isAdmin) {
    return <Navigate to={routes.tonight} replace />
  }
  return <Outlet />
}
