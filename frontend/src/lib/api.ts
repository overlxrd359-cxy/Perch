/**
 * 统一请求封装。
 *
 * 约定：
 * 1. access token 只存在内存（Zustand），不写 localStorage —— 防 XSS 窃取。
 * 2. refresh token 由后端放在 httpOnly Cookie 里，前端拿不到，靠 credentials: 'include' 自动携带。
 * 3. 错误一律抛 ApiError，按 code 分支，不要匹配 message 文本。
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export interface ApiErrorBody {
  code: string
  message: string
  request_id?: string
  details?: unknown
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly requestId?: string

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.name = 'ApiError'
    this.status = status
    this.code = body.code
    this.requestId = body.request_id
  }
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  token?: string | null
  signal?: AbortSignal
}

function parseJson(text: string): unknown {
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, token, signal } = options

  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: 'include',
    signal,
  })

  if (response.status === 204) return undefined as T

  const data = parseJson(await response.text())

  if (!response.ok) {
    const fallback: ApiErrorBody = {
      code: 'unknown_error',
      message: `请求失败（${response.status}）`,
    }
    throw new ApiError(response.status, (data as ApiErrorBody) ?? fallback)
  }

  return data as T
}