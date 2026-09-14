import type { AuthUser } from '@/stores/authStore'

/**
 * El avatar: color de la paleta y, encima, el emoji elegido o la inicial del nombre.
 *
 * La inicial como respaldo y no una silueta genérica: con dos personas usando la app,
 * una silueta no distingue a nadie, y la inicial sí sin pedir que subas una foto. El
 * texto va siempre oscuro porque los seis colores de la paleta son claros a propósito
 * —se eligieron para contrastar con tinta oscura—, así que no hace falta calcularlo.
 */
export function Avatar({
  user,
  size = 32,
}: {
  user: Pick<AuthUser, 'avatarColor' | 'avatarEmoji' | 'displayName' | 'username'>
  size?: number
}) {
  const inicial = (user.displayName || user.username || '?').trim().charAt(0).toUpperCase()

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
