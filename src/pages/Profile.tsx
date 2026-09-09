import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { BadgeCheck, ShieldAlert } from 'lucide-react'
import { Button } from '@/components/atoms/Button'
import { Field } from '@/components/atoms/Field'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import {
  NOCHE_END_HOUR,
  NOCHE_START_HOUR,
  useUiStore,
  type Theme,
} from '@/stores/uiStore'
import {
  changePassword,
  logout,
  startEmailVerification,
  updateProfile,
  verifyEmail,
  type ProfilePatch,
} from '@/api/auth'
import { ApiError } from '@/lib/apiClient'
import { routes } from '@/router/paths'
import { useAuthStore } from '@/stores/authStore'

const MIN_PASSWORD = 12

const inputStyle = {
  background: 'var(--mf-surf-2)',
  border: '1px solid var(--mf-line-strong)',
} as const

function message(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback
}

export function ProfilePage() {
  const user = useAuthStore((s) => s.user)
  if (!user) return null

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <SleepPreferences />
      <AppearanceCard />
      <AccountCard />
      <PasswordCard />
      <SignOutCard />
      <p className="px-2 text-body-sm opacity-60">
        Morfeo es una herramienta de hábitos, no un dispositivo médico. Si el insomnio
        persiste, lo valora un profesional del sueño.
      </p>
    </div>
  )
}

function SleepPreferences() {
  const user = useAuthStore((s) => s.user)!
  const queryClient = useQueryClient()
  const [patch, setPatch] = useState<ProfilePatch>({})
  const save = useMutation({
    mutationFn: () => updateProfile(patch),
    // Cambiar la hora de despertar mueve la recomendación: sin invalidarla, la portada
    // seguía enseñando la anterior y parecía que el perfil no se había guardado.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tonight'] }),
  })

  const wakeTime = patch.default_wake_time ?? user.defaultWakeTime
  const sleepNeed = patch.sleep_need_minutes ?? user.sleepNeedMinutes
  const latency = patch.declared_latency_minutes ?? user.declaredLatencyMinutes

  return (
    <SurfaceCard className="flex flex-col gap-4">
      <h2 className="text-headline-sm font-bold">Tus horarios</h2>

      <label className="flex flex-col gap-1 text-body-sm font-semibold">
        Hora a la que necesitas levantarte
        <input
          type="time"
          value={wakeTime.slice(0, 5)}
          onChange={(e) =>
            setPatch((p) => ({ ...p, default_wake_time: `${e.target.value}:00` }))
          }
          className="min-h-touch rounded-md px-3 font-normal"
          style={inputStyle}
        />
      </label>

      <label className="flex flex-col gap-1 text-body-sm font-semibold">
        Cuánto sueño necesitas ({Math.floor(sleepNeed / 60)} h {sleepNeed % 60} min)
        <input
          type="range"
          min={300}
          max={660}
          step={15}
          value={sleepNeed}
          onChange={(e) => setPatch((p) => ({ ...p, sleep_need_minutes: Number(e.target.value) }))}
        />
      </label>

      <label className="flex flex-col gap-1 text-body-sm font-semibold">
        Cuánto sueles tardar en dormirte ({latency} min)
        <input
          type="range"
          min={0}
          max={120}
          step={5}
          value={latency}
          onChange={(e) =>
            setPatch((p) => ({ ...p, declared_latency_minutes: Number(e.target.value) }))
          }
        />
        <span className="font-normal opacity-70">
          En cuanto haya noches medidas manda el dato del reloj, no este.
        </span>
      </label>

      <Button
        fullWidth
        onClick={() => save.mutate()}
        disabled={Object.keys(patch).length === 0 || save.isPending}
      >
        {save.isPending ? 'Guardando…' : 'Guardar'}
      </Button>
      {save.isSuccess ? (
        <p role="status" className="text-body-sm" style={{ color: 'var(--mf-good)' }}>
          Guardado.
        </p>
      ) : null}
    </SurfaceCard>
  )
}

/**
 * Cuenta y email.
 *
 * El email es opcional y solo sirve para recuperar la contraseña, así que la tarjeta
 * lo dice: sin esa frase, un campo de email en una app de sueño parece obligatorio o
 * parece que se va a usar para algo más.
 */
/**
 * El tema, y sobre todo el automático.
 *
 * El modo noche solo sirve si está puesto **cuando estás en la cama**, que es justo
 * cuando menos apetece buscar un botón. Por eso el interruptor de verdad es el
 * automático, y el selector manual está debajo: quien lo toque está diciendo que
 * prefiere decidirlo él, y entonces el automático se apaga solo.
 */
function AppearanceCard() {
  const theme = useUiStore((s) => s.theme)
  const setTheme = useUiStore((s) => s.setTheme)
  const autoNoche = useUiStore((s) => s.autoNoche)
  const setAutoNoche = useUiStore((s) => s.setAutoNoche)

  const opciones: { value: Theme; label: string; hint: string }[] = [
    { value: 'light', label: 'Claro', hint: 'De día' },
    { value: 'dark', label: 'Oscuro', hint: 'Por defecto' },
    { value: 'noche', label: 'Noche profunda', hint: 'Ámbar, sin blancos' },
  ]

  return (
    <SurfaceCard className="flex flex-col gap-4">
      <div>
        <h2 className="text-headline-sm font-bold">Aspecto</h2>
        <p className="mt-1 text-body-sm opacity-70">
          El modo noche profunda quita los blancos y los azules. No es capricho: la luz
          azul es la que más frena la melatonina, y el tema oscuro normal sigue teniendo
          bastante.
        </p>
      </div>

      <label className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={autoNoche}
          onChange={(e) => setAutoNoche(e.target.checked)}
          className="mt-1 size-5 shrink-0"
        />
        <span>
          <span className="font-semibold">Activarlo solo de noche</span>
          <span className="block text-body-sm opacity-70">
            De {String(NOCHE_START_HOUR).padStart(2, '0')}:00 a{' '}
            {String(NOCHE_END_HOUR).padStart(2, '0')}:00. Si eliges un tema a mano, esto
            se apaga.
          </span>
        </span>
      </label>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-body-sm font-semibold">Tema</legend>
        <div className="flex flex-wrap gap-2">
          {opciones.map((opcion) => (
            <button
              key={opcion.value}
              type="button"
              onClick={() => setTheme(opcion.value)}
              aria-pressed={theme === opcion.value}
              className="min-h-touch flex-1 rounded-md px-3 py-2 text-left focus-visible:outline-none focus-visible:ring-2"
              style={{
                background:
                  theme === opcion.value ? 'var(--mf-primary)' : 'var(--mf-surf-2)',
                color: theme === opcion.value ? 'var(--mf-on-primary)' : undefined,
                border: '1px solid var(--mf-line-strong)',
              }}
            >
              <span className="block font-semibold">{opcion.label}</span>
              <span className="block text-body-sm opacity-80">{opcion.hint}</span>
            </button>
          ))}
        </div>
      </fieldset>
    </SurfaceCard>
  )
}

function AccountCard() {
  const user = useAuthStore((s) => s.user)!
  const [email, setEmail] = useState(user.email ?? '')
  const [code, setCode] = useState('')
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const request = useMutation({
    mutationFn: () => startEmailVerification(email.trim()),
    onSuccess: (data) =>
      setNotice(
        data.sent_by_email
          ? `Código enviado a ${data.email}. Caduca en 15 minutos.`
          : `El servidor no tiene correo configurado, así que el código está en su consola. Caduca en 15 minutos.`,
      ),
    onError: (err) => setError(message(err, 'No se pudo enviar el código.')),
  })

  const confirm = useMutation({
    mutationFn: () => verifyEmail(code.trim()),
    onSuccess: () => {
      setNotice('Email confirmado.')
      setCode('')
    },
    onError: (err) => setError(message(err, 'No se pudo confirmar el código.')),
  })

  function reset() {
    setNotice(null)
    setError(null)
  }

  return (
    <SurfaceCard className="flex flex-col gap-4">
      <h2 className="text-headline-sm font-bold">Cuenta</h2>

      <div>
        <p className="text-body-sm opacity-60">Usuario</p>
        <p className="font-bold">{user.username}</p>
      </div>

      <div className="flex items-center gap-2 text-body-sm">
        {user.email ? (
          user.emailVerified ? (
            <>
              <BadgeCheck aria-hidden size={16} style={{ color: 'var(--mf-good)' }} />
              <span>{user.email} · confirmado</span>
            </>
          ) : (
            <>
              <ShieldAlert aria-hidden size={16} style={{ color: 'var(--mf-chart-awake)' }} />
              <span>{user.email} · sin confirmar</span>
            </>
          )
        ) : (
          <span className="opacity-70">Sin email. La cuenta funciona igual.</span>
        )}
      </div>

      <label className="flex flex-col gap-1 text-body-sm font-semibold">
        {user.email ? 'Cambiar el email' : 'Añadir un email'}
        <input
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value)
            reset()
          }}
          className="min-h-touch rounded-md px-3 font-normal"
          style={inputStyle}
        />
        <span className="font-normal opacity-70">
          Opcional, y solo sirve para recuperar la contraseña si se te olvida.
        </span>
      </label>

      <Button
        variant="secondary"
        onClick={() => {
          reset()
          request.mutate()
        }}
        disabled={!email.trim() || request.isPending}
      >
        {request.isPending ? 'Enviando…' : 'Enviarme un código'}
      </Button>

      {request.isSuccess ? (
        <div className="flex items-end gap-2">
          <label className="flex flex-1 flex-col gap-1 text-body-sm font-semibold">
            Código
            <input
              inputMode="numeric"
              maxLength={8}
              value={code}
              onChange={(e) => {
                setCode(e.target.value)
                reset()
              }}
              className="min-h-touch rounded-md px-3 font-normal tabular-nums"
              style={inputStyle}
            />
          </label>
          <Button onClick={() => confirm.mutate()} disabled={!code.trim() || confirm.isPending}>
            Confirmar
          </Button>
        </div>
      ) : null}

      {notice ? (
        <p role="status" className="text-body-sm" style={{ color: 'var(--mf-good)' }}>
          {notice}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="text-body-sm text-error">
          {error}
        </p>
      ) : null}
    </SurfaceCard>
  )
}

function PasswordCard() {
  const navigate = useNavigate()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [error, setError] = useState<string | null>(null)

  const change = useMutation({
    mutationFn: () => changePassword(current, next),
    onSuccess: async () => {
      // El backend revoca todos los refresh, incluido el de esta pestaña: quedarse
      // aquí solo llevaría al siguiente 401. Mejor salir limpio y volver a entrar.
      useAuthStore.getState().clearSession()
      navigate(routes.login, { replace: true })
    },
    onError: (err) => setError(message(err, 'No se pudo cambiar la contraseña.')),
  })

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    change.mutate()
  }

  return (
    <SurfaceCard>
      <h2 className="mb-1 text-headline-sm font-bold">Cambiar la contraseña</h2>
      <p className="mb-4 text-body-sm opacity-70">
        Se cierran todas las sesiones, también esta: si alguien tenía la contraseña
        anterior, cambiarla sin echarlo no le quitaría el acceso.
      </p>

      <form onSubmit={onSubmit} noValidate>
        <Field
          id="current-password"
          label="Contraseña actual"
          type="password"
          autoComplete="current-password"
          required
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
        />
        <Field
          id="new-password"
          label="Contraseña nueva"
          type="password"
          autoComplete="new-password"
          required
          value={next}
          onChange={(e) => setNext(e.target.value)}
        />
        <p className="mb-3 text-body-sm opacity-70">
          Mínimo {MIN_PASSWORD} caracteres, con mayúscula, minúscula y número.
        </p>

        {error ? (
          <p role="alert" className="mb-3 text-body-sm text-error">
            {error}
          </p>
        ) : null}

        <Button
          type="submit"
          fullWidth
          disabled={!current || !next || change.isPending}
        >
          {change.isPending ? 'Cambiando…' : 'Cambiar y volver a entrar'}
        </Button>
      </form>
    </SurfaceCard>
  )
}

function SignOutCard() {
  const navigate = useNavigate()
  return (
    <SurfaceCard>
      <Button
        variant="ghost"
        onClick={async () => {
          await logout()
          navigate(routes.login, { replace: true })
        }}
      >
        Cerrar sesión
      </Button>
    </SurfaceCard>
  )
}
