export const routes = {
  login: '/login',
  onboarding: '/empezar',
  tonight: '/',
  checkin: '/check-in',
  history: '/historial',
  connect: '/reloj',
  profile: '/perfil',
  dev: '/dev',
  devUser: (userId: string) => `/dev/${userId}`,
  notFound: '*',
} as const
