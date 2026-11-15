import { Link } from 'react-router-dom'

/**
 * 注册页。M1-14 实现表单与校验，M0 只占位。
 */
export function Register() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">注册</h2>
        <p className="mt-1 text-sm text-slate-500">M1 阶段在这里接学号 / 邮箱 / 密码表单</p>
      </div>

      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm leading-6 text-slate-500">
        注册功能尚未实现。规则先记着：密码至少 10 位、拒绝弱口令、注册后需邮箱验证。
      </div>

      <p className="text-xs text-slate-400">
        已有账号？
        <Link to="/login" className="ml-1 text-slate-900 underline-offset-2 hover:underline">
          去登录
        </Link>
      </p>
    </div>
  )
}