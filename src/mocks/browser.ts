/**
 * Arranque del mock del navegador.
 *
 * MSW y sus handlers se cargan con `import()` dinámico y no en el nivel del módulo:
 * así el bundle de producción no arrastra la librería de mocks ni los datos de
 * ejemplo cuando hay una API real configurada, que es la mayoría de los despliegues.
 */
export async function startMockWorker() {
  if (typeof window === 'undefined') return

  if (import.meta.env.DEV) {
    // Dev usa el proxy de Vite hacia el mock en Node (8787). Se desregistra cualquier
    // service worker previo para no acabar con dos capas de mocks a la vez.
    if ('serviceWorker' in navigator) {
      const regs = await navigator.serviceWorker.getRegistrations()
      await Promise.all(regs.map((r) => r.unregister()))
    }
    return
  }

  // Los mocks en un build son **opt-in**. Antes se activaban cuando VITE_API_BASE_URL
  // estaba vacío, y eso es exactamente el caso del despliegue real, donde el backend
  // sirve el frontend desde su mismo origen: la app habría enseñado datos inventados
  // con toda la naturalidad. Ahora hay que pedirlos, y solo lo hace el e2e.
  if (import.meta.env.VITE_ENABLE_MOCKS !== 'true') return

  try {
    const [{ setupWorker }, { handlers }] = await Promise.all([
      import('msw/browser'),
      import('@/mocks/handlers'),
    ])
    await setupWorker(...handlers).start({
      onUnhandledRequest: 'bypass',
      serviceWorker: { url: '/mockServiceWorker.js' },
      quiet: true,
    })
  } catch (error) {
    console.warn('[MSW] Service worker no disponible.', error)
  }
}
