import { useEffect } from 'react'
import { useUiStore } from '@/stores/uiStore'

export function useTheme() {
  const theme = useUiStore((s) => s.theme)
  const setTheme = useUiStore((s) => s.setTheme)
  const toggleTheme = useUiStore((s) => s.toggleTheme)
  return { theme, setTheme, toggleTheme }
}

/** Cada minuto: basta para que el cambio de franja se note al momento sin coste. */
const TICK_MS = 60_000

/**
 * Vigila la hora para encender y apagar el modo noche profunda.
 *
 * Va con intervalo **y** con `visibilitychange` porque en el móvil no basta el
 * primero: al bloquear la pantalla el navegador congela los temporizadores, así que
 * una app abierta desde las ocho y mirada a las doce se despertaría en el tema de
 * antes justo en el momento en que el otro hace falta.
 */
export function useNightThemeWatcher() {
  const syncNightTheme = useUiStore((s) => s.syncNightTheme)

  useEffect(() => {
    syncNightTheme()
    const timer = setInterval(() => syncNightTheme(), TICK_MS)
    const onVisible = () => {
      if (document.visibilityState === 'visible') syncNightTheme()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [syncNightTheme])
}
