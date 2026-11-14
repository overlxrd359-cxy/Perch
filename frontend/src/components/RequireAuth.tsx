import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { isAdmin, useAuth, type Role } from '../lib/auth'

interface RequireAuthProps {
  /** 不传表示只要求登录；传了则要求角色命中 */
  roles?: Role[]
}

/**
 * 路由守卫。
 *
 * 注意：这只是用户体验层的拦截，真正的鉴权永远在后端。
 * 前端做不了的越权，后端必须挡住。
 */
export function RequireAuth({ roles }: RequireAuthProps) {
  const user = useAuth((s) => s.user)
  const location = useLocation()

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (roles && roles.length > 0) {
    const allowed = roles.includes(user.role) || (roles.includes('admin') && isAdmin(user.role))
    if (!allowed) {
      return <Navigate to="/" replace />
    }
  }

  return <Outlet />
}