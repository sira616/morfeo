import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Moon } from 'lucide-react'
import { Button } from '@/components/atoms/Button'
import { Field } from '@/components/atoms/Field'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { login, register } from '@/api/auth'
import { ApiError } from '@/lib/apiClient'
import { routes } from '@/router/paths'

export function LoginPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      const user = mode === 'login' ? await login(email, password) : await register(email, password)
      // `next` viene de RequireAuth: se vuelve a donde se intentaba entrar.
      const next = params.get('next')
      navigate(user.onboardingDone ? (next ?? routes.tonight) : routes.onboarding, {
        replace: true,
      })
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'No se pudo conectar. Inténtalo de nuevo.',
      )
    } finally {
      setPending(false)
    }
  }

  return (
    <main
      className="grid min-h-dvh place-items-center p-6 text-ink"
      style={{ background: 'var(--mf-canvas-radial)' }}
    >
      <SurfaceCard className="w-full max-w-sm">
        <div className="mb-4 flex items-center gap-2">
          <Moon aria-hidden size={24} />
          <h1 className="text-headline-md font-bold">Morfeo</h1>
        </div>
        <p className="mb-4 text-body-sm opacity-70">
          Te dice a qué hora meterte en la cama, no a qué hora dormirte.
        </p>

        <form onSubmit={onSubmit} noValidate>
          <Field
            id="email"
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Field
            id="password"
            label="Contraseña"
            type="password"
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error ? (
            <p role="alert" className="mb-3 text-body-sm text-error">
              {error}
            </p>
          ) : null}

          <Button type="submit" fullWidth disabled={pending}>
            {pending ? 'Un momento…' : mode === 'login' ? 'Entrar' : 'Crear cuenta'}
          </Button>
        </form>

        <Button
          variant="ghost"
          fullWidth
          className="mt-2"
          onClick={() => {
            setMode(mode === 'login' ? 'register' : 'login')
            setError(null)
          }}
        >
          {mode === 'login' ? 'No tengo cuenta' : 'Ya tengo cuenta'}
        </Button>
      </SurfaceCard>
    </main>
  )
}
