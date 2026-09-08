import { Moon, Sun } from 'lucide-react'
import { IconButton } from '@/components/atoms/IconButton'
import { useUiStore } from '@/stores/uiStore'

/** Toggle light/dark — dark is the default theme. */
export function ThemeToggle({ className }: { className?: string }) {
  const theme = useUiStore((s) => s.theme)
  const toggleTheme = useUiStore((s) => s.toggleTheme)
  const isDark = theme === 'dark'

  return (
    <IconButton
      label={isDark ? 'Activar modo claro' : 'Activar modo oscuro'}
      onClick={toggleTheme}
      className={className}
    >
      {isDark ? <Sun size={18} aria-hidden /> : <Moon size={18} aria-hidden />}
    </IconButton>
  )
}
