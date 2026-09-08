import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex min-h-touch items-center justify-center gap-2 rounded-xl px-md text-body-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-on-primary hover:bg-primary-container',
        secondary:
          'bg-secondary-container text-on-secondary-container hover:bg-secondary-fixed',
        outline:
          'border border-outline-variant bg-transparent text-ink hover:bg-surf-2',
        ghost: 'text-ink hover:bg-surf-2',
        danger: 'bg-error text-on-error hover:opacity-90',
        brand: '',
      },
      size: {
        default: 'h-11 px-4 py-2',
        sm: 'h-9 min-h-0 rounded-lg px-3 text-xs',
        lg: 'h-12 rounded-2xl px-6 text-base',
        icon: 'h-10 w-10 min-h-0',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type = 'button', style, ...props }, ref) => {
    const brandStyle =
      variant === 'brand'
        ? {
            color: 'var(--mf-on-brand)',
            background:
              'linear-gradient(145deg, var(--mf-brand-yellow), #e6c22e 45%, var(--mf-brand-green))',
            boxShadow:
              'var(--mf-shadow-brand), inset 0 1px 0 var(--mf-inset-shine)',
            ...style,
          }
        : style

    return (
      <button
        ref={ref}
        type={type}
        className={cn(
          buttonVariants({ variant, size }),
          variant === 'brand' && 'pa-cta',
          className,
        )}
        style={brandStyle}
        {...props}
      />
    )
  },
)
Button.displayName = 'Button'
