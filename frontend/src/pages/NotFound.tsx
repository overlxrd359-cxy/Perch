import { Link } from 'react-router-dom'

/** 404 页。 */
export function NotFound() {
  return (
    <div className="flex min-h-full flex-col items-center justify-center gap-3 px-4 py-16 text-center">
      <p className="text-4xl font-semibold text-slate-900">404</p>
      <p className="text-sm text-slate-500">这个页面不存在，可能是链接过期了。</p>
      <Link
        to="/"
        className="mt-2 rounded-md bg-slate-900 px-4 py-2 text-sm text-white transition-colors hover:bg-slate-700"
      >
        回首页
      </Link>
    </div>
  )
}