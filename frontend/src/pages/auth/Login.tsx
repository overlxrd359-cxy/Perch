import { Link } from 'react-router-dom'

/**
 * 登录页。M1-14 实现表单与接口调用，M0 只占位，避免做出“假登录”。
 */
export function Login() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">登录</h2>
        <p className="mt-1 text-sm text-slate-500">M1 阶段在这里接学号 + 密码表单</p>
      </div>

      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm leading-6 text-slate-500">
        登录功能尚未实现。当前为 M0 骨架，直接访问
        <Link to="/" className="mx-1 text-slate-900 underline-offset-2 hover:underline">
          首页
        </Link>
        可以看到前端已经跑起来。
      </div>

      <p className="text-xs text-slate-400">账号由学校统一学号注册，管理员不从公开注册页创建。</p>
    </div>
  )
}