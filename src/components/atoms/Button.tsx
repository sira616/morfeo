import { cva, type VariantProps } from 'class-variance-authority'
import type { ButtonHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex min-h-touch items-center justify-center gap-2 rounded-md px-4 text-body-sm font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-primary text-on-primary hover:bg-primary-container',
        secondary:
          'bg-secondary-container text-on-secondary-container hover:bg-secondary-fixed',
        hint: 'bg-tertiary-fixed text-on-tertiary-fixed hover:bg-tertiary-fixed-dim',
        ghost:
          'bg-transparent text-on-surface hover:bg-surface-container-high',
        danger: 'bg-error text-on-error hover:bg-error/90',
      },
      fullWidth: {
        true: 'w-full',
        false: '',
      },
    },
    defaultVariants: {
      variant: 'primary',
      fullWidth: false,
    },
  },
)

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>

export function Button({
  className,
  variant,
  fullWidth,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(buttonVariants({ variant, fullWidth }), className)}
      {...props}
    />
  )
}
