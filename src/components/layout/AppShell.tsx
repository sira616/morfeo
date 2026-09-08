import { NavLink, Outlet } from 'react-router-dom'
import { Moon } from 'lucide-react'
import { ThemeToggle } from '@/components/molecules/ThemeToggle'
import { NAV } from '@/components/layout/nav'
import { cn } from '@/lib/utils'
import { routes } from '@/router/paths'
import { useAuthStore } from '@/stores/authStore'

/**
 * Dos formas distintas del mismo shell, no una estirada.
 *
 * En móvil, barra de navegación abajo, donde llega el pulgar. A partir de `lg`, barra
 * lateral y un lienzo ancho: una columna de móvil centrada en un monitor de 1440 px se
 * ve como un teléfono pegado en medio de la pantalla, y eso no se arregla con padding.
 */
export function AppShell() {
  const user = useAuthStore((s) => s.user)

  return (
    <div
      className="flex h-dvh flex-col overflow-hidden text-ink lg:flex-row"
      style={{ background: 'var(--mf-canvas-radial)' }}
    >
      {/* --- Barra lateral, solo en escritorio --- */}
      <aside
        className="safe-top hidden shrink-0 flex-col gap-1 border-r px-3 py-4 lg:flex lg:w-60"
        style={{ background: 'var(--mf-surf-1)', borderColor: 'var(--mf-line)' }}
      >
        <NavLink
          to={routes.tonight}
          className="mb-4 flex items-center gap-2 rounded-md px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo"
        >
          <Moon aria-hidden size={22} />
          <span className="text-headline-md font-bold">Morfeo</span>
        </NavLink>

        <nav className="flex flex-col gap-1" aria-label="Secciones">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end
              className={({ isActive }) =>
                cn(
                  'flex min-h-touch items-center gap-3 rounded-lg px-3 text-body-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo',
                  isActive ? 'font-bold' : 'opacity-70 hover:opacity-100',
                )
              }
              style={({ isActive }) =>
                isActive ? { background: 'var(--mf-surf-3)' } : undefined
              }
            >
              <Icon aria-hidden size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto flex items-center justify-between gap-2 px-3">
          {user ? (
            <span className="truncate text-body-sm opacity-60">{user.displayName}</span>
          ) : null}
          <ThemeToggle />
        </div>
      </aside>

      {/* --- Cabecera, solo en móvil --- */}
      <header
        className="safe-top safe-sides flex shrink-0 items-center justify-between gap-4 border-b px-4 py-2 lg:hidden"
        style={{ background: 'var(--mf-surf-1)', borderColor: 'var(--mf-line)' }}
      >
        <NavLink
          to={routes.tonight}
          className="flex items-center gap-2 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo"
        >
          <Moon aria-hidden size={20} />
          <span className="text-headline-md font-bold">Morfeo</span>
        </NavLink>
        <div className="flex items-center gap-2">
          {user ? <span className="text-sm opacity-70">{user.displayName}</span> : null}
          <ThemeToggle />
        </div>
      </header>

      <main className="safe-scroll-bottom mx-auto w-full max-w-6xl min-h-0 flex-1 overflow-x-hidden overflow-y-auto px-4 pt-4 lg:px-8 lg:py-8">
        <Outlet />
      </main>

      {/* --- Barra inferior, solo en móvil: la app se usa de noche y con una mano --- */}
      <nav
        className="safe-bottom safe-sides fixed inset-x-0 bottom-0 z-50 flex justify-around border-t px-2 py-1 lg:hidden"
        style={{ background: 'var(--mf-surf-1)', borderColor: 'var(--mf-line)' }}
        aria-label="Secciones"
      >
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end
            className={({ isActive }) =>
              cn(
                'flex min-h-touch min-w-touch flex-col items-center justify-center gap-0.5 rounded-md px-3 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo',
                isActive ? 'font-bold opacity-100' : 'opacity-60',
              )
            }
          >
            <Icon aria-hidden size={20} />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
