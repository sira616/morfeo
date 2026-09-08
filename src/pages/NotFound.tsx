import { Link } from 'react-router-dom'
import { routes } from '@/router/paths'

export function NotFoundPage() {
  return (
    <main className="grid min-h-dvh place-items-center p-6 text-center">
      <div>
        <h1 className="text-headline-md font-bold">Esta página no existe</h1>
        <Link to={routes.tonight} className="mt-2 inline-block underline">
          Volver a esta noche
        </Link>
      </div>
    </main>
  )
}
