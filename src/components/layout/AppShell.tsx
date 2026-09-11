import { NavLink, Outlet } from 'react-router-dom'
import { Moon } from 'lucide-react'
import { ThemeToggle } from '@/components/molecules/ThemeToggle'
import { ADMIN_NAV, NAV } from '@/components/layout/nav'
import { cn } from '@/lib/utils'
import { routes } from '@/router/paths'
import { useAuthStore } from '@/stores/authStore'

/**
 * Una cabecera arriba en todos los tamaños, y en el móvil además la barra inferior.
 *
 * Antes, en escritorio, había barra lateral. Se quitó porque conseguía lo contrario de
 * lo que buscaba: se comía 240 px fijos y empujaba el contenido a una franja estrecha
 * en medio, con lo que un monitor grande enseñaba una app de móvil centrada entre dos
 * márgenes enormes. Con la navegación arriba, el ancho entero es para el contenido.
 *
 * La barra inferior del móvil se queda: ahí el problema es el contrario —el pulgar no
 * llega arriba— y la app se usa de noche y con una mano.
 */
export function AppShell() {
  const user = useAuthStore((s) => s.user)
  // La cabecera tiene ancho de sobra para el panel; la inferior del móvil no: cinco
  // iconos ya llenan el ancho del pulgar.
  const headerNav = user?.isAdmin ? [...NAV, ...ADMIN_NAV] : NAV

  return (
    <div
      className="flex h-dvh flex-col overflow-hidden text-ink"
      style={{ background: 'var(--mf-canvas-radial)' }}
    >
      <header
        className="safe-top safe-sides flex shrink-0 items-center gap-4 border-b px-4 py-2 lg:px-8"
        style={{ background: 'var(--mf-surf-1)', borderColor: 'var(--mf-line)' }}
      >
        <NavLink
          to={routes.tonight}
          className="flex shrink-0 items-center gap-2 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo"
        >
          <Moon aria-hidden size={20} />
          <span className="text-headline-md font-bold">Morfeo</span>
        </NavLink>

        {/* Solo en escritorio: en el móvil esto mismo vive abajo, al alcance del pulgar. */}
        <nav className="hidden items-center gap-1 lg:flex" aria-label="Secciones">
          {headerNav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end
              className={({ isActive }) =>
                cn(
                  'flex min-h-touch items-center gap-2 rounded-lg px-3 text-body-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo',
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

        <div className="ml-auto flex shrink-0 items-center gap-2">
          {user ? (
            <span className="max-w-40 truncate text-body-sm opacity-70">
              {user.displayName}
            </span>
          ) : null}
          <ThemeToggle />
        </div>
      </header>

      {/* El tope es alto, pero existe: sin ninguno, en un ultrapanorámico una línea de
          texto cruzaría la pantalla entera y dejaría de leerse. 1760 px dan sitio a
          tres columnas de tarjetas holgadas, que es donde se acaba lo que hay que
          enseñar. */}
      <main className="safe-scroll-bottom mx-auto min-h-0 w-full max-w-[1760px] flex-1 overflow-x-hidden overflow-y-auto px-4 pt-4 lg:px-8 lg:py-8">
        <Outlet />
      </main>

      {/* --- Barra inferior, solo en móvil --- */}
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
