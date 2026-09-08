export {}

declare global {
  interface Window {
    __e2eNavigate?: (to: string) => void
  }
}
