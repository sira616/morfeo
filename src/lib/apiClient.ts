import { useAuthStore } from '@/stores/authStore'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown
  accessToken?: string | null
  skipAuthRefresh?: boolean
}

function serializeBody(body: unknown): { body: BodyInit; contentType?: string } {
  if (body instanceof FormData) {
    return { body }
  }
  if (body instanceof URLSearchParams) {
    return { body, contentType: 'application/x-www-form-urlencoded' }
  }
  if (typeof body === 'string') {
    return { body }
  }
  return { body: JSON.stringify(body), contentType: 'application/json' }
}

function parseErrorMessage(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null
  const record = data as Record<string, unknown>
  if (typeof record.error === 'string' && record.error) return record.error
  if (typeof record.detail === 'string' && record.detail) return record.detail
  return null
}

let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  const refreshToken = useAuthStore.getState().refreshToken
  if (!refreshToken) return false

  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!response.ok) return false
    const data = (await response.json()) as {
      access_token: string
      refresh_token: string
    }
    useAuthStore.getState().setTokens({
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    })
    return true
  } catch {
    return false
  }
}

/**
 * Typed fetch wrapper. Bearer from memory; on 401 refreshes once then logout.
 */
export async function apiClient<T>(
  path: string,
  {
    body,
    accessToken,
    headers,
    skipAuthRefresh,
    ...init
  }: RequestOptions = {},
): Promise<T> {
  const serialized = body !== undefined ? serializeBody(body) : null
  const token = accessToken ?? useAuthStore.getState().accessToken

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(serialized?.contentType ? { 'Content-Type': serialized.contentType } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: serialized?.body,
  })

  if (response.status === 401 && !skipAuthRefresh && path !== '/api/auth/refresh') {
    if (!refreshPromise) {
      refreshPromise = tryRefresh().finally(() => {
        refreshPromise = null
      })
    }
    const refreshed = await refreshPromise
    if (refreshed) {
      return apiClient<T>(path, {
        body,
        headers,
        skipAuthRefresh: true,
        ...init,
      })
    }
    useAuthStore.getState().clearSession()
    throw new ApiError(401, 'Sesión expirada')
  }

  if (!response.ok) {
    let message = 'Something went wrong'
    try {
      const data: unknown = await response.json()
      message = parseErrorMessage(data) ?? message
    } catch {
      if (response.status === 404) {
        message =
          'No se encontró la API. Recarga la página o reinicia el servidor de desarrollo.'
      }
    }
    throw new ApiError(response.status, message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
