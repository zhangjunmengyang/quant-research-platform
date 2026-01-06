/**
 * Strategy UI State Store (Zustand)
 */

import { create } from 'zustand'
import type { Strategy, StrategyListParams } from './types'

interface StrategyUIState {
  // Selected strategy for detail
  selectedStrategy: Strategy | null
  setSelectedStrategy: (strategy: Strategy | null) => void

  // List filters
  filters: StrategyListParams
  setFilters: (filters: Partial<StrategyListParams>) => void
  resetFilters: () => void

  // Backtest form state
  backtestFormOpen: boolean
  openBacktestForm: () => void
  closeBacktestForm: () => void
}

const defaultFilters: StrategyListParams = {
  page: 1,
  page_size: 50,
  order_by: 'created_at',
}

export const useStrategyStore = create<StrategyUIState>((set) => ({
  // Selected strategy
  selectedStrategy: null,
  setSelectedStrategy: (strategy) => set({ selectedStrategy: strategy }),

  // Filters
  filters: defaultFilters,
  setFilters: (newFilters) =>
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
    })),
  resetFilters: () => set({ filters: defaultFilters }),

  // Backtest form
  backtestFormOpen: false,
  openBacktestForm: () => set({ backtestFormOpen: true }),
  closeBacktestForm: () => set({ backtestFormOpen: false }),
}))
