import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Button } from '@/components/atoms/Button'
import { Card } from '@/components/atoms/Card'

type Props = { children: ReactNode }
type State = { hasError: boolean }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(_error: Error, _info: ErrorInfo) {
    /* Log to monitoring in production — never show technical details to users */
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-dvh items-center justify-center px-md">
          <Card className="w-full max-w-sm text-center">
            <h1 className="text-headline-md text-on-surface">Algo ha fallado</h1>
            <p className="mt-sm text-body-sm text-on-surface-variant">
              Recarga la página e inténtalo de nuevo.
            </p>
            <Button
              className="mt-md"
              fullWidth
              onClick={() => window.location.assign('/')}
            >
              Volver al inicio
            </Button>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}
