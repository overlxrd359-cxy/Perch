import { Link } from 'react-router-dom'

/**
 * 用户端首页。M0 只验证路由与布局，真实内容在 M1/M3 填。
 */
export function Home() {
  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-900">M0 骨架已就位</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          前后端骨架、健康检查、日志与数据库会话已经打通。业务功能从 M1（注册登录）开始，
          座位图与预约在 M3。
        </p>
        <div className="mt-4 flex flex-wrap gap-3 text-sm">
          <Link
            to="/rooms"
            className="rounded-md bg-slate-900 px-4 py-2 text-white transition-colors hover:bg-slate-700"
          >
            去看找座页
          </Link>
          <Link
            to="/admin"
            className="rounded-md border border-slate-300 px-4 py-2 text-slate-700 transition-colors hover:bg-slate-100"
          >
            管理端入口
          </Link>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="text-sm font-medium text-slate-900">当前阶段</h3>
          <p className="mt-1 text-sm text-slate-500">M0 工程地基</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="text-sm font-medium text-slate-900">下一步</h3>
          <p className="mt-1 text-sm text-slate-500">M1 认证与安全基线</p>
        </div>
      </section>
    </div>
  )
}