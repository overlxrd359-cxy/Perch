/**
 * 统一请求封装。
 *
 * 约定：
 * 1. access token 只存内存，不写 localStorage（防 XSS 窃取）
 * 2. refresh token 由后端下发放 httpOnly Cookie，前端不可见
 * 3. 错误抛 ApiError，按 code 分支
 *
 * TODO(M0)：
 * - [ ] apiRequest<T>()
 * - [ ] ApiError 类
 * - [ ] 204 无 body 处理
 */
export {}
