import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'

import { useAuth } from '../lib/auth'

const navClass = ({ isActive }: { isActive: boolean }): string =>
  isActive ? 'font-medium text-slate-900' : 'text-slate-500 hover:text-slate-900'

export function UserLayout() {
  const user = useAuth((s) => s.user)
  const clearSession = useAuth((s) => s.clearSession)
  const navigate = useNavigate()

  function handleLogout() {
    clearSession()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-3xl items-center justify-between px-4">
          <Link to="/" className="text-sm font-semibold tracking-tight">
            智能自习室
          </Link>
          <nav className="flex items-center gap-5 text-sm">
            <NavLink to="/" end className={navClass}>
              首页
            </NavLink>
            <NavLink to="/rooms" className={navClass}>
              找座
            </NavLink>
            <button
              type="button"
              onClick={handleLogout}
              className="text-slate-400 transition-colors hover:text-slate-900"
            >
              退出
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">
        {user ? (
          <p className="mb-4 text-sm text-slate-500">
            {user.name} · {user.studentNo}
          </p>
        ) : null}
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 py-4 text-center text-xs text-slate-400">
        Campus Seat · M0 骨架
      </footer>
    </div>
  )
}