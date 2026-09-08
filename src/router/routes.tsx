import { Navigate, Route, Routes } from 'react-router-dom'
import { RequireAuth } from '@/router/RequireAuth'
import { routes } from '@/router/paths'
import { AppShell } from '@/components/layout/AppShell'
import { LoginPage } from '@/pages/Login'
import { OnboardingPage } from '@/pages/Onboarding'
import { TonightPage } from '@/pages/Tonight'
import { CheckinPage } from '@/pages/Checkin'
import { HistoryPage } from '@/pages/History'
import { ConnectPage } from '@/pages/Connect'
import { ProfilePage } from '@/pages/Profile'
import { NotFoundPage } from '@/pages/NotFound'
import { DevPage, DevUserPage } from '@/pages/Dev'
import { RequireAdmin } from '@/router/RequireAdmin'
import { useAuthStore } from '@/stores/authStore'

/**
 * Sin onboarding no hay hora de despertar, y sin hora de despertar no hay nada que
 * calcular: la portada redirige en vez de enseñar una recomendación inventada.
 */
function TonightOrOnboarding() {
  const user = useAuthStore((s) => s.user)
  if (user && !user.onboardingDone) {
    return <Navigate to={routes.onboarding} replace />
  }
  return <TonightPage />
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path={routes.login} element={<LoginPage />} />

      <Route element={<RequireAuth />}>
        <Route path={routes.onboarding} element={<OnboardingPage />} />
        <Route element={<AppShell />}>
          <Route path={routes.tonight} element={<TonightOrOnboarding />} />
          <Route path={routes.checkin} element={<CheckinPage />} />
          <Route path={routes.history} element={<HistoryPage />} />
          <Route path={routes.connect} element={<ConnectPage />} />
          <Route path={routes.profile} element={<ProfilePage />} />
          <Route element={<RequireAdmin />}>
            <Route path={routes.dev} element={<DevPage />} />
            <Route path="/dev/:userId" element={<DevUserPage />} />
          </Route>
        </Route>
      </Route>

      <Route path={routes.notFound} element={<NotFoundPage />} />
    </Routes>
  )
}
