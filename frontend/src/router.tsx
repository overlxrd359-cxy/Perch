import { createBrowserRouter } from 'react-router-dom'

import { AdminLayout } from './layouts/AdminLayout'
import { AuthLayout } from './layouts/AuthLayout'
import { UserLayout } from './layouts/UserLayout'
import { Dashboard } from './pages/admin/Dashboard'
import { Login } from './pages/auth/Login'
import { Register } from './pages/auth/Register'
import { NotFound } from './pages/NotFound'
import { Home } from './pages/user/Home'
import { Rooms } from './pages/user/Rooms'

/**
 * 路由表（双端共用一个工程）。
 *
 * M0 只做骨架：三个布局 + 占位页，**不接登录态**。
 * M1-15 起用 <RequireAuth> 包住 / 与 /admin 两组路由，
 * 未登录跳 /login、角色不匹配跳 /。
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
    element: <UserLayout />,
    children: [
      { index: true, element: <Home /> },
      { path: '/rooms', element: <Rooms /> },
    ],
  },
  {
    element: <AdminLayout />,
    children: [{ path: '/admin', element: <Dashboard /> }],
  },
  { path: '*', element: <NotFound /> },
])