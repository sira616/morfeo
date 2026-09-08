import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/utils'

type IconButtonProps = {
  children: ReactNode
  label: string
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children' | 'aria-label'>

export function IconButton({ children, label, className, ...props }: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      className={cn(
        'grid h-[38px] w-[38px] place-items-center rounded-[11px] text-ink-dim transition-colors duration-200',
        'hover:text-ink',
        className,
      )}
      style={{
        background: 'var(--mf-surf-1)',
        border: '1px solid var(--mf-line)',
      }}
      {...props}
    >
      {children}
    </button>
  )
}
