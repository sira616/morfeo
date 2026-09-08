import { NavLink, Outlet } from 'react-router-dom'
import { CalendarRange, Moon, MessageCircle, User, Watch } from 'lucide-react'
import { ThemeToggle } from '@/components/molecules/ThemeToggle'
import { cn } from '@/lib/utils'
import { routes } from '@/router/paths'
import { useAuthStore } from '@/stores/authStore'

const NAV = [
  { to: routes.tonight, label: 'Esta noche', icon: Moon, end: true },
  { to: routes.checkin, label: 'Check-in', icon: MessageCircle, end: true },
  { to: routes.history, label: 'Historial', icon: CalendarRange, end: true },
  { to: routes.connect, label: 'Reloj', icon: Watch, end: true },
  { to: routes.profile, label: 'Perfil', icon: User, end: true },
]

export function AppShell() {
  const user = useAuthStore((s) => s.user)

  return (
    <div
      className="flex h-dvh flex-col overflow-hidden text-ink"
      style={{ background: 'var(--mf-canvas-radial)' }}
    >
      <header
        className="flex min-h-touch shrink-0 items-center justify-between gap-4 border-b px-4"
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

      <main className="mx-auto min-h-0 w-full max-w-3xl flex-1 overflow-x-hidden overflow-y-auto px-4 pb-24 pt-4">
        <Outlet />
      </main>

      {/* Navegación abajo: la app se usa de noche, con una mano y el móvil en la cama. */}
      <nav
        className="fixed inset-x-0 bottom-0 z-50 flex justify-around border-t px-2 py-1"
        style={{ background: 'var(--mf-surf-1)', borderColor: 'var(--mf-line)' }}
        aria-label="Secciones"
      >
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
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
