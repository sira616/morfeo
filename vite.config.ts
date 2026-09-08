import { defineConfig, loadEnv, type Plugin, type ViteDevServer } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'
import type { Server } from 'node:http'
import { createServer } from '@mswjs/http-middleware'

const MOCK_PORT = 8787
const MOCK_HOST = '127.0.0.1'

let mockServer: Server | null = null

async function stopMockServer(): Promise<void> {
  const current = mockServer
  mockServer = null
  if (!current) return
  await new Promise<void>((resolve) => {
    current.close(() => resolve())
  })
}

async function ensureMockServer(
  server: ViteDevServer,
  { force = false }: { force?: boolean } = {},
): Promise<void> {
  if (!force && mockServer?.listening) return
  await stopMockServer()
  const mod = (await server.ssrLoadModule('/src/mocks/handlers.ts')) as {
    handlers: Parameters<typeof createServer>
  }
  const app = createServer(...mod.handlers)
  await new Promise<void>((resolve, reject) => {
    const httpServer = app.listen(MOCK_PORT, MOCK_HOST, () => {
      mockServer = httpServer
      resolve()
    })
    httpServer.once('error', (err: NodeJS.ErrnoException) => {
      if (err.code === 'EADDRINUSE') {
        mockServer = null
        resolve()
        return
      }
      reject(err)
    })
  })
}

function mswDevPlugin(): Plugin {
  return {
    name: 'msw-dev-server',
    configureServer(server) {
      const handlersFile = path.resolve(__dirname, 'src/mocks/handlers.ts')
      server.watcher.add(handlersFile)
      server.watcher.on('change', (file) => {
        if (path.resolve(file) === handlersFile) {
          void ensureMockServer(server, { force: true })
        }
      })
      server.httpServer?.once('close', () => {
        void stopMockServer()
      })
      return async () => {
        await ensureMockServer(server)
      }
    },
    async closeBundle() {
      await stopMockServer()
    },
  }
}

/**
 * El frontend siempre pide a `/api/...` en su propio origen y es el proxy quien
 * decide a dónde va eso. Así el código de la app no sabe si detrás hay mocks o
 * backend, y en desarrollo no hay CORS de por medio.
 *
 * - Sin `VITE_API_TARGET`: arranca el servidor de mocks (MSW) y apunta ahí.
 * - Con `VITE_API_TARGET`: no arranca mocks y apunta al backend real.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '')
  const backendTarget = env.VITE_API_TARGET?.trim()
  const useMocks = !backendTarget
  const target = backendTarget ?? `http://${MOCK_HOST}:${MOCK_PORT}`

  if (!useMocks) {
    console.log(`\n  API → ${target} (backend real, mocks desactivados)\n`)
  }

  return {
    plugins: [react(), tailwindcss(), ...(useMocks ? [mswDevPlugin()] : [])],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
          // El check-in llega por SSE: sin esto el proxy acumula la respuesta en un
          // búfer y el chat aparece de golpe al final en vez de ir escribiéndose.
          configure: (proxy) => {
            proxy.on('proxyRes', (proxyRes) => {
              if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
                proxyRes.headers['cache-control'] = 'no-cache, no-transform'
              }
            })
          },
        },
      },
    },
  }
})
