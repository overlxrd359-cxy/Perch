import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ApiError, apiRequest } from '../../lib/api'
import { isAdmin, useAuth, type CurrentUser } from '../../lib/auth'

interface LoginResponse {
  access_token: string
  user: CurrentUser
}

export function Login() {
  const navigate = useNavigate()
  const setSession = useAuth((s) => s.setSession)

  const [studentNo, setStudentNo] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const data = await apiRequest<LoginResponse>('/auth/login', {
        method: 'POST',
        body: { student_no: studentNo, password },
      })
      setSession(data.access_token, data.user)
      navigate(isAdmin(data.user.role) ? '/admin' : '/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '网络异常，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div className="space-y-1">
        <label htmlFor="studentNo" className="text-sm font-medium text-slate-700">
          学号
        </label>
        <input
          id="studentNo"
          autoComplete="username"
          required
          value={studentNo}
          onChange={(e) => setStudentNo(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="password" className="text-sm font-medium text-slate-700">
          密码
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
        />
      </div>

      {error ? (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {loading ? '登录中…' : '登录'}
      </button>

      <p className="text-center text-sm text-slate-500">
        还没有账号？
        <Link to="/register" className="ml-1 text-slate-900 underline-offset-4 hover:underline">
          注册
        </Link>
      </p>
    </form>
  )
}