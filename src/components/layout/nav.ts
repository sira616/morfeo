import {
  CalendarRange,
  MessageCircle,
  Moon,
  ShieldCheck,
  User,
  Watch,
  type LucideIcon,
} from 'lucide-react'
import { routes } from '@/router/paths'

export type NavItem = {
  to: string
  label: string
  icon: LucideIcon
}

/** Único sitio donde vive la lista: la barra lateral y la inferior leen de aquí. */
export const NAV: NavItem[] = [
  { to: routes.tonight, label: 'Esta noche', icon: Moon },
  { to: routes.checkin, label: 'Check-in', icon: MessageCircle },
  { to: routes.history, label: 'Historial', icon: CalendarRange },
  { to: routes.connect, label: 'Reloj', icon: Watch },
  { to: routes.profile, label: 'Perfil', icon: User },
]

/** Solo para administradores. La puerta de verdad está en el backend, que responde
 *  404 a quien no lo es; esto evita enseñar un enlace que no lleva a ninguna parte. */
export const ADMIN_NAV: NavItem[] = [{ to: routes.dev, label: 'Dev', icon: ShieldCheck }]
