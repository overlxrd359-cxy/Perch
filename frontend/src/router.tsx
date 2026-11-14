/**
 * 路由表（双端）。
 *
 * 结构：
 *   /login /register        -> AuthLayout
 *   /  /rooms ...           -> 需登录，UserLayout（移动优先）
 *   /admin ...              -> 需 admin 角色，AdminLayout（桌面优先）
 *
 * TODO(M0)：
 * - [ ] createBrowserRouter 三组路由
 * - [ ] RequireAuth 包裹登录区与管理区
 */
export {}
