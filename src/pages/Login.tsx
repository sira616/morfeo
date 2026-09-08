import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Moon } from 'lucide-react'
import { Button } from '@/components/atoms/Button'
import { Field } from '@/components/atoms/Field'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { login, register } from '@/api/auth'
import { ApiError } from '@/lib/apiClient'
import { routes } from '@/router/paths'

const MIN_PASSWORD = 12

/**
 * Entrar y registrarse en la misma tarjeta.
 *
 * La identidad es el **nombre de usuario**: esto se usa entre un par de personas en
 * una red doméstica, y pedir un correo para entrar en tu propia app de sueño no aporta
 * nada. El email es opcional y solo sirve para recuperar la contraseña; el campo lo
 * dice, en vez de dejar que la gente lo adivine.
 */
export function LoginPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [loginName, setLoginName] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  const registering = mode === 'register'
  const tooShort = registering && password.length > 0 && password.length < MIN_PASSWORD

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      const user = registering
        ? await register(loginName, password, email.trim() || undefined)
        : await login(loginName, password)
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
      className="safe-top safe-bottom safe-sides grid min-h-dvh place-items-center p-6 text-ink"
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
            id="login"
            label={registering ? 'Usuario' : 'Usuario o email'}
            autoComplete={registering ? 'username' : 'username'}
            required
            value={loginName}
            onChange={(e) => setLoginName(e.target.value)}
          />

          {registering ? (
            <Field
              id="email"
              label="Email (opcional)"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          ) : null}

          <Field
            id="password"
            label="Contraseña"
            type="password"
            autoComplete={registering ? 'new-password' : 'current-password'}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {registering ? (
            <p
              className="mb-3 text-body-sm"
              style={{ color: tooShort ? 'var(--mf-chart-awake)' : undefined, opacity: 0.75 }}
            >
              Mínimo {MIN_PASSWORD} caracteres, con mayúscula, minúscula y número. El email
              solo sirve para recuperarla si se te olvida.
            </p>
          ) : null}

          {error ? (
            <p role="alert" className="mb-3 text-body-sm text-error">
              {error}
            </p>
          ) : null}

          <Button type="submit" fullWidth disabled={pending}>
            {pending ? 'Un momento…' : registering ? 'Crear cuenta' : 'Entrar'}
          </Button>
        </form>

        <Button
          variant="ghost"
          fullWidth
          className="mt-2"
          onClick={() => {
            setMode(registering ? 'login' : 'register')
            setError(null)
          }}
        >
          {registering ? 'Ya tengo cuenta' : 'No tengo cuenta'}
        </Button>
      </SurfaceCard>
    </main>
  )
}
