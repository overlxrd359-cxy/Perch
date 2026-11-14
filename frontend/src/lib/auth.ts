import { create } from 'zustand'

export type Role = 'student' | 'reviewer' | 'admin' | 'super_admin'

export interface CurrentUser {
  id: number
  name: string
  studentNo: string
  role: Role
}

interface AuthState {
  /** 只放内存，刷新页面时靠 refresh cookie 重新换发 */
  accessToken: string | null
  user: CurrentUser | null
  setSession: (accessToken: string, user: CurrentUser) => void
  clearSession: () => void
}

export const useAuth = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  setSession: (accessToken, user) => set({ accessToken, user }),
  clearSession: () => set({ accessToken: null, user: null }),
}))

export function isAdmin(role: Role | undefined): boolean {
  return role === 'admin' || role === 'super_admin'
}