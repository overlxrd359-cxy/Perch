import { Link, Outlet } from 'react-router-dom'

import { useAuth } from '../lib/auth'

/** 侧栏条目。未实现的模块先标灰，避免点进去 404。 */
const navItems: { to: string; label: string; ready: boolean }[] = [
  { to: '/admin', label: '仪表盘', ready: true },
  { to: '/admin/rooms', label: '自习室与座位', ready: false },
  { to: '/admin/reservations', label: '预约管理', ready: false },
  { to: '/admin/users', label: '用户管理', ready: false },
  { to: '/admin/audit', label: '审计日志', ready: false },
  { to: '/admin/settings', label: '系统配置', ready: false },
]

export function AdminLayout() {
  const user = useAuth((s) => s.user)

  return (
    <div className="flex min-h-full">
      <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white md:block">
        <div className="flex h-14 items-center border-b border-slate-200 px-4">
          <Link to="/admin" className="text-sm font-semibold tracking-tight">
            管理后台
          </Link>
        </div>
        <nav className="flex flex-col gap-1 p-3">
          {navItems.map((item) =>
            item.ready ? (
              <Link
                key={item.to}
                to={item.to}
                className="rounded-md px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              >
                {item.label}
              </Link>
            ) : (
              <span
                key={item.to}
                className="cursor-not-allowed rounded-md px-3 py-2 text-sm text-slate-300"
                title="后续里程碑实现"
              >
                {item.label}
              </span>
            ),
          )}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-4">
          <span className="text-sm text-slate-500">管理后台</span>
          <span className="text-sm text-slate-500">
            {user ? `${user.name} · ${user.role}` : ''}
          </span>
        </header>
        <main className="flex-1 bg-slate-50 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}