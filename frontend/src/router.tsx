import { createBrowserRouter } from 'react-router-dom'

import { RequireAuth } from './components/RequireAuth'
import { AdminLayout } from './layouts/AdminLayout'
import { AuthLayout } from './layouts/AuthLayout'
import { UserLayout } from './layouts/UserLayout'
import { NotFound } from './pages/NotFound'
import { Dashboard } from './pages/admin/Dashboard'
import { Login } from './pages/auth/Login'
import { Register } from './pages/auth/Register'
import { Home } from './pages/user/Home'
import { Rooms } from './pages/user/Rooms'

/**
 * 路由结构：
 *   /login /register        -> AuthLayout
 *   /  /rooms ...           -> 需登录，UserLayout（移动优先）
 *   /admin ...              -> 需 admin 角色，AdminLayout（桌面优先）
 *
 * 前端守卫只是体验层，真正的鉴权在后端。
 */
export const router = createBrowserRouter([
  {
    element: <AuthLayout />,
    children: [
      { path: '/login', element: <Login /> },
      { path: '/register', element: <Register /> },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <UserLayout />,
        children: [
          { index: true, element: <Home /> },
          { path: '/rooms', element: <Rooms /> },
        ],
      },
    ],
  },
  {
    element: <RequireAuth roles={['admin']} />,
    children: [
      {
        path: '/admin',
        element: <AdminLayout />,
        children: [{ index: true, element: <Dashboard /> }],
      },
    ],
  },
  { path: '*', element: <NotFound /> },
])