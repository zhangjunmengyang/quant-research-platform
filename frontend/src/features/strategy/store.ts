/**
 * Strategy UI State Store (Zustand)
 * 只存储 UI 状态，不存储 filters（filters 由 URL search params 管理）
 */

import { create } from 'zustand'
import type { Strategy } from './types'

interface StrategyUIState {
  // Selected strategy for detail
  selectedStrategy: Strategy | null
  setSelectedStrategy: (strategy: Strategy | null) => void

  // Backtest form state
  backtestFormOpen: boolean
  openBacktestForm: () => void
  closeBacktestForm: () => void
}

export const useStrategyStore = create<StrategyUIState>((set) => ({
  // Selected strategy
  selectedStrategy: null,
  setSelectedStrategy: (strategy) => set({ selectedStrategy: strategy }),

  // Backtest form
  backtestFormOpen: false,
  openBacktestForm: () => set({ backtestFormOpen: true }),
  closeBacktestForm: () => set({ backtestFormOpen: false }),
}))

// 默认 filters 配置（供组件使用）
export const DEFAULT_STRATEGY_FILTERS = {
  page: 1,
  page_size: 50,
  order_by: 'created_at',
} as const
