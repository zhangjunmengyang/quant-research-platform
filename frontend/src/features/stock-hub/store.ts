/**
 * Stock Hub UI State Store (Zustand)
 * 只存储 UI 状态，filters 由 URL search params 管理
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { StockFactorMeta, StockFactorConfig } from './types'
import { DEFAULT_STOCK_FACTOR_VISIBLE_COLUMNS } from './types'

interface StockHubUIState {
  // 因子详情面板
  selectedFactor: StockFactorMeta | null
  detailPanelOpen: boolean
  openDetailPanel: (factor: StockFactorMeta) => void
  closeDetailPanel: () => void

  // 表格列配置
  visibleColumns: string[]
  setVisibleColumns: (cols: string[]) => void
  columnWidths: Record<string, number>
  setColumnWidth: (key: string, width: number) => void

  // 回测面板 tab
  backtestTab: 'config' | 'history' | 'analysis'
  setBacktestTab: (tab: 'config' | 'history' | 'analysis') => void

  // 待加入回测的因子队列（从浏览器页面添加）
  pendingFactors: StockFactorConfig[]
  addPendingFactor: (name: string) => void
  removePendingFactor: (name: string) => void
  clearPendingFactors: () => void
}

export const useStockHubStore = create<StockHubUIState>()(
  persist(
    (set) => ({
      selectedFactor: null,
      detailPanelOpen: false,
      openDetailPanel: (factor) => set({ selectedFactor: factor, detailPanelOpen: true }),
      closeDetailPanel: () => set({ detailPanelOpen: false }),

      visibleColumns: [...DEFAULT_STOCK_FACTOR_VISIBLE_COLUMNS],
      setVisibleColumns: (cols) => set({ visibleColumns: cols }),
      columnWidths: {},
      setColumnWidth: (key, width) =>
        set((state) => ({
          columnWidths: { ...state.columnWidths, [key]: width },
        })),

      backtestTab: 'config',
      setBacktestTab: (tab) => set({ backtestTab: tab }),

      pendingFactors: [],
      addPendingFactor: (name) =>
        set((state) => {
          if (state.pendingFactors.some((f) => f.name === name)) return state
          return {
            pendingFactors: [
              ...state.pendingFactors,
              { name, ascending: true, param: '静态', weight: 1 },
            ],
          }
        }),
      removePendingFactor: (name) =>
        set((state) => ({
          pendingFactors: state.pendingFactors.filter((f) => f.name !== name),
        })),
      clearPendingFactors: () => set({ pendingFactors: [] }),
    }),
    {
      name: 'stock-hub-ui-storage',
      partialize: (state) => ({
        visibleColumns: state.visibleColumns,
        columnWidths: state.columnWidths,
        backtestTab: state.backtestTab,
        pendingFactors: state.pendingFactors,
      }),
    }
  )
)
