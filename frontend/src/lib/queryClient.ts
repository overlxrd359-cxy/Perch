import { QueryClient } from '@tanstack/react-query'

/**
 * 全局 QueryClient。
 *
 * 约定：
 * - retry: 1 —— 只重试一次，别把 4xx 也重试到死
 * - staleTime: 30s —— 座位图这类数据 30 秒内不重复请求
 * - refetchOnWindowFocus: false —— 后台切回来不自动刷，避免抢座时请求突增
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
})