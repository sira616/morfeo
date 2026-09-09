import { Moon, MoonStar, Sun } from 'lucide-react'
import { IconButton } from '@/components/atoms/IconButton'
import { useUiStore, type Theme } from '@/stores/uiStore'

/**
 * Cicla claro → oscuro → noche profunda.
 *
 * El icono y la etiqueta son los del tema **siguiente**, no los del actual: un botón
 * que muestra dónde estás no dice qué pasa al pulsarlo, que es lo único que se
 * pregunta quien lo mira.
 */
const NEXT: Record<Theme, { theme: Theme; label: string; Icon: typeof Moon }> = {
  light: { theme: 'dark', label: 'Activar modo oscuro', Icon: Moon },
  dark: { theme: 'noche', label: 'Activar modo noche profunda', Icon: MoonStar },
  noche: { theme: 'light', label: 'Activar modo claro', Icon: Sun },
}

export function ThemeToggle({ className }: { className?: string }) {
  const theme = useUiStore((s) => s.theme)
  const toggleTheme = useUiStore((s) => s.toggleTheme)
  const { label, Icon } = NEXT[theme]

  return (
    <IconButton label={label} onClick={toggleTheme} className={className}>
      <Icon size={18} aria-hidden />
    </IconButton>
  )
}
