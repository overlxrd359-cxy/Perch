import { Link } from 'react-router-dom'

export function NotFound() {
  return (
    <div className="flex min-h-full flex-col items-center justify-center gap-3 px-4 text-center">
      <p className="text-sm font-medium text-slate-400">404</p>
      <h1 className="text-lg font-semibold tracking-tight text-slate-900">这个页面不存在</h1>
      <Link to="/" className="text-sm text-slate-600 underline-offset-4 hover:underline">
        回到首页
      </Link>
    </div>
  )
}