import { useState, type FormEvent, type ReactNode } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { BadgeCheck, ShieldAlert } from 'lucide-react'
import { Button } from '@/components/atoms/Button'
import { Field } from '@/components/atoms/Field'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { Avatar } from '@/components/atoms/Avatar'
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
    // Agrupado por categorías en vez de una rejilla plana de tarjetas sueltas: así se
    // sabe de un vistazo qué hay dónde —quién eres, tu sueño, el aspecto, la cuenta— en
    // lugar de tener que leer cada tarjeta para ubicarla. Dentro de cada categoría las
    // tarjetas se reparten en columnas para llenar el ancho del escritorio.
    <div className="mx-auto flex max-w-[1600px] flex-col gap-8">
      <ProfileCategory title="Tú" hint="Cómo te ves y qué te mueve.">
        <IdentityCard />
        <AboutYouCard />
      </ProfileCategory>

      <ProfileCategory title="Tu sueño" hint="Lo que el motor usa para calcular la hora.">
        <SleepPreferences />
      </ProfileCategory>

      <ProfileCategory title="Aspecto" hint="Cómo se ve la app.">
        <AppearanceCard />
      </ProfileCategory>

      <ProfileCategory title="Cuenta" hint="Acceso y seguridad.">
        <AccountCard />
        <PasswordCard />
        <SignOutCard />
      </ProfileCategory>

      <p className="px-2 text-body-sm opacity-60">
        Morfeo es una herramienta de hábitos, no un dispositivo médico. Si el insomnio
        persiste, lo valora un profesional del sueño.
      </p>
    </div>
  )
}

/**
 * Una categoría de ajustes: un encabezado y, debajo, sus tarjetas repartidas en
 * columnas. El encabezado es lo que convierte una lista de tarjetas en un mapa: dice
 * de qué va este bloque sin que haya que entrar en cada tarjeta a averiguarlo.
 */
function ProfileCategory({
  title,
  hint,
  children,
}: {
  title: string
  hint: string
  children: ReactNode
}) {
  return (
    <section className="flex flex-col gap-3">
      <div className="border-b pb-2" style={{ borderColor: 'var(--mf-line)' }}>
        <h2 className="text-headline-sm font-bold">{title}</h2>
        <p className="text-body-sm opacity-60">{hint}</p>
      </div>
      <div className="grid items-start gap-6 lg:grid-cols-2">{children}</div>
    </section>
  )
}

/** Los seis colores de avatar. Cerrados a propósito: todos claros, para que el texto
 *  oscuro de encima contraste sin tener que calcular nada. Coinciden con el backend. */
const AVATAR_COLORS = [
  '#4fd6a0',
  '#6c5ce7',
  '#f4b860',
  '#f0797b',
  '#6688ff',
  '#3fd1c0',
] as const

/**
 * Identidad: el avatar, el nombre para mostrar, el color y un emoji.
 *
 * Todo esto es cosmético y no toca ningún cálculo, pero es lo que hace que la app sea
 * «la mía» y no una hoja de cálculo: con dos personas compartiéndola, un avatar con
 * color distingue de un vistazo quién ha entrado.
 */
function IdentityCard() {
  const user = useAuthStore((s) => s.user)!
  const queryClient = useQueryClient()
  const [patch, setPatch] = useState<ProfilePatch>({})
  const save = useMutation({
    mutationFn: () => updateProfile(patch),
    onSuccess: () => {
      setPatch({})
      queryClient.invalidateQueries({ queryKey: ['dev'] })
    },
  })

  // La vista previa mezcla lo guardado con lo que se está tocando, para ver el avatar
  // cambiar mientras eliges, no después de guardar.
  const preview = {
    ...user,
    displayName: patch.display_name ?? user.displayName,
    avatarColor: patch.avatar_color ?? user.avatarColor,
    avatarEmoji: patch.avatar_emoji !== undefined ? patch.avatar_emoji : user.avatarEmoji,
  }

  return (
    <SurfaceCard className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <Avatar user={preview} size={52} />
        <div>
          <h3 className="text-headline-sm font-bold">Identidad</h3>
          <p className="text-body-sm opacity-70">Cómo te ves tú y cómo te ve la otra persona.</p>
        </div>
      </div>

      <label className="flex flex-col gap-1 text-body-sm font-semibold">
        Nombre para mostrar
        <input
          type="text"
          maxLength={120}
          value={patch.display_name ?? user.displayName}
          onChange={(e) => setPatch((p) => ({ ...p, display_name: e.target.value }))}
          className="min-h-touch rounded-md px-3 font-normal"
          style={inputStyle}
        />
      </label>

      <fieldset className="flex flex-col gap-2">
        <legend className="text-body-sm font-semibold">Color</legend>
        <div className="mt-1 flex flex-wrap gap-2">
          {AVATAR_COLORS.map((color) => {
            const activo = (patch.avatar_color ?? user.avatarColor) === color
            return (
              <button
                key={color}
                type="button"
                aria-label={color}
                aria-pressed={activo}
                onClick={() => setPatch((p) => ({ ...p, avatar_color: color }))}
                className="size-9 rounded-full focus-visible:outline-none focus-visible:ring-2"
                style={{
                  background: color,
                  boxShadow: activo ? `0 0 0 2px var(--mf-bg-0), 0 0 0 4px ${color}` : undefined,
                }}
              />
            )
          })}
        </div>
      </fieldset>

      <label className="flex flex-col gap-1 text-body-sm font-semibold">
        Emoji (opcional)
        <div className="flex gap-2">
          <input
            type="text"
            value={patch.avatar_emoji ?? user.avatarEmoji ?? ''}
            onChange={(e) =>
              // Un emoji es un carácter, pero puede ocupar varias unidades UTF-16;
              // [...str] las agrupa bien y evita cortar uno por la mitad.
              setPatch((p) => ({ ...p, avatar_emoji: [...e.target.value].slice(0, 2).join('') || null }))
            }
            placeholder="🌙"
            className="min-h-touch w-24 rounded-md px-3 text-center text-xl font-normal"
            style={inputStyle}
          />
          <span className="self-center text-body-sm opacity-60">
            Vacío = la inicial de tu nombre.
          </span>
        </div>
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

const CHRONOTYPES: { value: NonNullable<ProfilePatch['chronotype']>; label: string; hint: string }[] = [
  { value: 'alondra', label: 'Alondra', hint: 'Rindes por la mañana' },
  { value: 'intermedio', label: 'Intermedio', hint: 'Ni una cosa ni otra' },
  { value: 'buho', label: 'Búho', hint: 'Rindes de noche' },
]

/**
 * Sobre ti: cronotipo y objetivo.
 *
 * El cronotipo **no cambia la hora recomendada** —esa se ancla en tu hora real de
 * despertar, que ya recoge tu ritmo—; ajusta el tono de los consejos. Decirlo evita la
 * decepción de elegir «búho» y no ver moverse nada. El objetivo es una frase tuya que
 * no entra en ningún cálculo: está para recordarte el porqué, que es lo que sostiene un
 * hábito cuando la novedad se pasa.
 */
function AboutYouCard() {
  const user = useAuthStore((s) => s.user)!
  const [patch, setPatch] = useState<ProfilePatch>({})
  const save = useMutation({ mutationFn: () => updateProfile(patch), onSuccess: () => setPatch({}) })

  const goal = patch.goal !== undefined ? patch.goal : user.goal
  const chronotype = patch.chronotype ?? user.chronotype
  const birthYear = patch.birth_year !== undefined ? patch.birth_year : user.birthYear
  const currentYear = new Date().getFullYear()

  return (
    <SurfaceCard className="flex flex-col gap-4">
      <h3 className="text-headline-sm font-bold">Sobre ti</h3>

      <fieldset className="flex flex-col gap-2">
        <legend className="text-body-sm font-semibold">Cronotipo</legend>
        <p className="text-body-sm opacity-60">
          No cambia la hora recomendada —esa sale de tu hora real de despertar—, solo el
          tono de los consejos.
        </p>
        <div className="mt-1 flex flex-wrap gap-2">
          {CHRONOTYPES.map((opcion) => {
            const activo = chronotype === opcion.value
            return (
              <button
                key={opcion.value}
                type="button"
                aria-pressed={activo}
                onClick={() => setPatch((p) => ({ ...p, chronotype: opcion.value }))}
                className="min-h-touch flex-1 rounded-md px-3 py-2 text-left focus-visible:outline-none focus-visible:ring-2"
                style={{
                  background: activo ? 'var(--mf-primary)' : 'var(--mf-surf-2)',
                  color: activo ? 'var(--mf-on-primary)' : undefined,
                  border: '1px solid var(--mf-line-strong)',
                }}
              >
                <span className="block font-semibold">{opcion.label}</span>
                <span className="block text-body-sm opacity-80">{opcion.hint}</span>
              </button>
            )
          })}
        </div>
      </fieldset>

      <label className="flex flex-col gap-1 text-body-sm font-semibold">
        Tu objetivo (opcional)
        <input
          type="text"
          maxLength={140}
          value={goal ?? ''}
          onChange={(e) => setPatch((p) => ({ ...p, goal: e.target.value || null }))}
          placeholder="Dormir mejor antes de las oposiciones"
          className="min-h-touch rounded-md px-3 font-normal"
          style={inputStyle}
        />
        <span className="font-normal opacity-60">Se te enseña en la portada. No entra en el cálculo.</span>
      </label>

      <label className="flex flex-col gap-1 text-body-sm font-semibold">
        Año de nacimiento (opcional)
        <input
          type="number"
          min={1900}
          max={currentYear - 13}
          value={birthYear ?? ''}
          onChange={(e) =>
            // Vacío borra (null); un año, se guarda. Se manda solo si es un año completo
            // y con sentido, para no pegar un patch por cada tecla mientras se escribe.
            setPatch((p) => {
              const raw = e.target.value
              if (raw === '') return { ...p, birth_year: null }
              const year = Number(raw)
              return year >= 1900 && year <= currentYear - 13
                ? { ...p, birth_year: year }
                : p
            })
          }
          placeholder="1995"
          className="min-h-touch rounded-md px-3 font-normal"
          style={inputStyle}
        />
        <span className="font-normal opacity-60">
          {birthYear
            ? `Tienes unos ${currentYear - birthYear} años. De momento solo es un dato tuyo; no cambia el cálculo.`
            : 'Guardamos el año, no la edad, para que no caduque cada cumpleaños.'}
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
  const weekend = patch.weekend_wake_time !== undefined ? patch.weekend_wake_time : user.weekendWakeTime
  const threshold = patch.poor_efficiency_threshold ?? user.poorEfficiencyThreshold

  return (
    <SurfaceCard className="flex flex-col gap-4">
      <h3 className="text-headline-sm font-bold">Tus horarios</h3>

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

      {/* El horario de finde es lo único de esta tarjeta que no es "tu media": es un
          segundo ancla para los días que cambias de ritmo. Va con casilla porque su
          estado por defecto —igual que entre semana— es una opción legítima, no un
          hueco por rellenar. */}
      <div className="flex flex-col gap-2">
        <label className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={weekend !== null}
            onChange={(e) =>
              setPatch((p) => ({
                ...p,
                weekend_wake_time: e.target.checked ? user.defaultWakeTime : null,
              }))
            }
            className="mt-1 size-5 shrink-0"
          />
          <span>
            <span className="font-semibold">Me levanto a otra hora el finde</span>
            <span className="block text-body-sm opacity-70">
              Se aplica a las noches de viernes y sábado, que despiertan en fin de semana.
            </span>
          </span>
        </label>
        {weekend !== null ? (
          <input
            type="time"
            aria-label="Hora de despertar el fin de semana"
            value={weekend.slice(0, 5)}
            onChange={(e) =>
              setPatch((p) => ({ ...p, weekend_wake_time: `${e.target.value}:00` }))
            }
            className="min-h-touch rounded-md px-3 font-normal"
            style={inputStyle}
          />
        ) : null}
      </div>

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

      {/* Ajuste fino, plegado para no competir con lo de arriba: casi nadie lo toca. */}
      <details className="text-body-sm">
        <summary className="cursor-pointer font-semibold opacity-80">Ajustes avanzados</summary>
        <div className="mt-3 flex flex-col gap-1">
          <label className="flex flex-col gap-1 font-semibold">
            Cuándo avisarte de una mala racha ({Math.round(threshold * 100)}% de eficiencia)
            <input
              type="range"
              min={0.7}
              max={0.95}
              step={0.01}
              value={threshold}
              onChange={(e) =>
                setPatch((p) => ({ ...p, poor_efficiency_threshold: Number(e.target.value) }))
              }
            />
            <span className="font-normal opacity-70">
              Eficiencia es el tiempo dormido frente al tiempo en la cama. Más alto = más
              exigente, avisa antes.
            </span>
          </label>
          <p className="mt-2 font-normal opacity-60">
            Zona horaria: {user.timezone}. Se detecta sola; escríbeme si vives en otra.
          </p>
        </div>
      </details>

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
        <h3 className="text-headline-sm font-bold">Aspecto</h3>
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
      <h3 className="text-headline-sm font-bold">Cuenta</h3>

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
      <h3 className="mb-1 text-headline-sm font-bold">Cambiar la contraseña</h3>
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
