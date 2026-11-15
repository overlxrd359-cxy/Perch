import { Outlet } from 'react-router-dom'

/**
 * 登录 / 注册布局：居中卡片。
 * 只负责壳，表单逻辑在 M1 实现。
 */
export function AuthLayout() {
  return (
    <div className="flex min-h-full flex-col items-center justify-center bg-slate-50 px-4 py-12">
      <div className="mb-6 text-center">
        <h1 className="text-xl font-semibold text-slate-900">Perch · 智能自习室</h1>
        <p className="mt-1 text-sm text-slate-500">找座、约座、签到，一个入口</p>
      </div>
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <Outlet />
      </div>
    </div>
  )
}