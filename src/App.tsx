import { useEffect } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ErrorBoundary } from '@/lib/errorBoundary'
import { E2eNavigateBridge } from '@/lib/e2eNavigateBridge'
import { AppRoutes } from '@/router/routes'
import { restoreSession } from '@/api/auth'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export default function App() {
  // Una vez al arrancar: canjea el refresh guardado para que recargar la página no
  // eche a nadie de la sesión.
  useEffect(() => {
    void restoreSession()
  }, [])

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <E2eNavigateBridge />
          <AppRoutes />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
