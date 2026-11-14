import { Outlet } from 'react-router-dom'

export function AuthLayout() {
  return (
    <div className="flex min-h-full items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">智能自习室</h1>
          <p className="mt-1 text-sm text-slate-500">找座、预约、签到，一个入口</p>
        </div>
        <Outlet />
      </div>
    </div>
  )
}