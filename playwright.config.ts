import { defineConfig, devices } from '@playwright/test'

const PORT = 4173
const BASE_URL = `http://127.0.0.1:${PORT}`

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
  },
  webServer: {
    // Construye en su propio directorio: `dist/` es el que sirve el backend en el
    // despliegue, y el e2e lo construye con los mocks activados. Compartirlos deja la
    // app real enseñando datos inventados en cuanto alguien corre los tests.
    command:
      `npx vite build --outDir dist-e2e && ` +
      `npx vite preview --outDir dist-e2e --host 127.0.0.1 --port ${PORT}`,
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      ...process.env,
      VITE_API_BASE_URL: process.env.VITE_API_BASE_URL ?? '',
      // El e2e corre contra el build real, así que los mocks hay que pedirlos.
      VITE_ENABLE_MOCKS: 'true',
    },
  },
  projects: [
    {
      // Chromium + iPhone viewport (doc mobile-first). Avoids WebKit install.
      name: 'Mobile Chrome',
      use: {
        ...devices['iPhone 13'],
        defaultBrowserType: 'chromium',
      },
    },
    {
      name: 'Desktop Chrome',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
