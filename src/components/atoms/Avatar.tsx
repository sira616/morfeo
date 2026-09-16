import type { AuthUser } from '@/stores/authStore'

/**
 * El avatar, con tres niveles de respaldo: la foto si la hay; si no, el emoji elegido
 * sobre el color; y si tampoco, la inicial del nombre.
 *
 * La inicial como último recurso y no una silueta genérica: con dos personas usando la
 * app, una silueta no distingue a nadie, y la inicial sí sin pedir que subas nada. El
 * texto va siempre oscuro porque los seis colores de la paleta son claros a propósito
 * —se eligieron para contrastar con tinta oscura—, así que no hace falta calcularlo.
 *
 * La foto llega como data URL ya validado por el backend (solo raster, ver
 * app/core/avatar.py), así que pintarla en un <img> es seguro.
 */
export function Avatar({
  user,
  size = 32,
}: {
  user: Pick<AuthUser, 'avatarColor' | 'avatarEmoji' | 'displayName' | 'username' | 'avatarUrl'>
  size?: number
}) {
  const inicial = (user.displayName || user.username || '?').trim().charAt(0).toUpperCase()

  if (user.avatarUrl) {
    return (
      <img
        src={user.avatarUrl}
        alt=""
        aria-hidden
        width={size}
        height={size}
        className="shrink-0 rounded-full object-cover"
        style={{ width: size, height: size }}
      />
    )
  }

  return (
    <span
      aria-hidden
      className="inline-flex shrink-0 items-center justify-center rounded-full font-bold leading-none"
      style={{
        width: size,
        height: size,
        background: user.avatarColor,
        color: '#0b0e14',
        fontSize: user.avatarEmoji ? size * 0.55 : size * 0.42,
      }}
    >
      {user.avatarEmoji || inicial}
    </span>
  )
}
