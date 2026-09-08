import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

declare global {
  interface Window {
    __e2eNavigate?: (to: string) => void
  }
}

/**
 * Exposes SPA navigate for Playwright.
 * Needed because access token lives in memory — full page reloads clear auth.
 */
export function E2eNavigateBridge() {
  const navigate = useNavigate()

  useEffect(() => {
    window.__e2eNavigate = (to: string) => {
      navigate(to)
    }
    return () => {
      delete window.__e2eNavigate
    }
  }, [navigate])

  return null
}
