import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ApiError, apiRequest } from '../../lib/api'

interface RegisterPayload {
  student_no: string
  name: string
  email: string
  password: string
}

export function Register() {
  const navigate = useNavigate()

  const [form, setForm] = useState<RegisterPayload>({
    student_no: '',
    name: '',
    email: '',
    password: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  function update<K extends keyof RegisterPayload>(key: K, value: RegisterPayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await apiRequest('/auth/register', { method: 'POST', body: form })
      navigate('/login', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '网络异常，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  const inputClass =
    'w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900'

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
          required
          value={form.student_no}
          onChange={(e) => update('student_no', e.target.value)}
          className={inputClass}
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="name" className="text-sm font-medium text-slate-700">
          姓名
        </label>
        <input
          id="name"
          required
          value={form.name}
          onChange={(e) => update('name', e.target.value)}
          className={inputClass}
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="email" className="text-sm font-medium text-slate-700">
          邮箱
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={form.email}
          onChange={(e) => update('email', e.target.value)}
          className={inputClass}
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="password" className="text-sm font-medium text-slate-700">
          密码
        </label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={10}
          value={form.password}
          onChange={(e) => update('password', e.target.value)}
          className={inputClass}
        />
        <p className="text-xs text-slate-400">至少 10 位，建议字母 + 数字组合</p>
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
        {loading ? '提交中…' : '注册'}
      </button>

      <p className="text-center text-sm text-slate-500">
        已有账号？
        <Link to="/login" className="ml-1 text-slate-900 underline-offset-4 hover:underline">
          登录
        </Link>
      </p>
    </form>
  )
}