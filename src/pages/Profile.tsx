import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/atoms/Button'
import { SurfaceCard } from '@/components/atoms/SurfaceCard'
import { logout, updateProfile, type ProfilePatch } from '@/api/auth'
import { routes } from '@/router/paths'
import { useAuthStore } from '@/stores/authStore'

export function ProfilePage() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const [patch, setPatch] = useState<ProfilePatch>({})

  const save = useMutation({ mutationFn: () => updateProfile(patch) })

  if (!user) return null

  const wakeTime = patch.default_wake_time ?? user.defaultWakeTime
  const sleepNeed = patch.sleep_need_minutes ?? user.sleepNeedMinutes
  const latency = patch.declared_latency_minutes ?? user.declaredLatencyMinutes

  return (
    <div className="flex flex-col gap-4">
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
            style={{ background: 'var(--mf-surf-2)', border: '1px solid var(--mf-line-strong)' }}
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
            onChange={(e) =>
              setPatch((p) => ({ ...p, sleep_need_minutes: Number(e.target.value) }))
            }
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
          <p role="status" className="text-body-sm opacity-80">
            Guardado.
          </p>
        ) : null}
      </SurfaceCard>

      <SurfaceCard>
        <p className="text-body-sm opacity-70">{user.email}</p>
        <Button
          variant="ghost"
          className="mt-2"
          onClick={async () => {
            await logout()
            navigate(routes.login, { replace: true })
          }}
        >
          Cerrar sesión
        </Button>
      </SurfaceCard>

      <p className="px-2 text-body-sm opacity-60">
        Morfeo es una herramienta de hábitos, no un dispositivo médico. Si el insomnio
        persiste, lo valora un profesional del sueño.
      </p>
    </div>
  )
}
