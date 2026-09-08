import { useUiStore } from '@/stores/uiStore'

export function useTheme() {
  const theme = useUiStore((s) => s.theme)
  const setTheme = useUiStore((s) => s.setTheme)
  const toggleTheme = useUiStore((s) => s.toggleTheme)
  return { theme, setTheme, toggleTheme }
}
