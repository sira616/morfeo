import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export type CardProps = HTMLAttributes<HTMLDivElement>

/** Level-1 surface: 1px border, 12px radius — no drop shadow */
export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-outline-variant bg-surface-container-lowest p-6 shadow-sm dark:shadow-none',
        className,
      )}
      {...props}
    />
  )
}
