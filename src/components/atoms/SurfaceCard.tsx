import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type SurfaceCardProps = {
  children: ReactNode
  className?: string
  padded?: boolean
}

/** Gradient surface card with top light line (redesign depth). */
export function SurfaceCard({
  children,
  className,
  padded = true,
}: SurfaceCardProps) {
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-[20px]',
        padded ? 'p-4' : null,
        className,
      )}
      style={{
        background: 'linear-gradient(160deg, var(--mf-surf-2), var(--mf-surf-1))',
        border: '1px solid var(--mf-line)',
        boxShadow: 'var(--mf-shadow-md)',
      }}
    >
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px"
        style={{
          background:
            'linear-gradient(90deg, transparent, var(--mf-sheen), transparent)',
        }}
        aria-hidden
      />
      {children}
    </div>
  )
}
