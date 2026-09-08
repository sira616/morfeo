import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { useUiStore } from '@/stores/uiStore'
import { startMockWorker } from '@/mocks/browser'

useUiStore.getState().setTheme(useUiStore.getState().theme)

async function bootstrap() {
  await startMockWorker()

  const rootElement = document.getElementById('root')
  if (!rootElement) {
    throw new Error('Root element #root not found')
  }

  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void bootstrap()
