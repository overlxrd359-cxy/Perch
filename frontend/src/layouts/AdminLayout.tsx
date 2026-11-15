import { NavLink, Outlet } from 'react-router-dom'

const navItems = [{ to: '/admin', label: '仪表盘', end: true }]

/**
 * 管理端布局（桌面优先）。
 * M5 起补齐自习室 / 预约 / 用户 / 审计 / 配置入口；M0 只保证壳能跑。
 */
export function AdminLayout() {
  return (
    <div className="flex min-h-full bg-slate-100">
      <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white md:block">
        <div className="flex h-14 items-center border-b border-slate-200 px-5">
          <span className="text-base font-semibold text-slate-900">Perch 管理端</span>
        </div>
        <nav className="flex flex-col gap-1 p-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center border-b border-slate-200 bg-white px-4 md:px-6">
          <span className="text-sm text-slate-500">管理后台</span>
        </header>
        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}