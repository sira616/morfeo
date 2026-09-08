import { defineConfig, type Plugin, type ViteDevServer } from 'vite'
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

const apiProxy = {
  '/api': {
    target: `http://${MOCK_HOST}:${MOCK_PORT}`,
    changeOrigin: true,
  },
} as const

export default defineConfig({
  plugins: [react(), tailwindcss(), mswDevPlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: { ...apiProxy },
  },
})
