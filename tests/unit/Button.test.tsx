import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Button } from '@/components/ui/button'

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Sign in</Button>)
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('can be disabled', () => {
    render(<Button disabled>Send</Button>)
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  })
})
