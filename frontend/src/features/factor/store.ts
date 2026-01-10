/**
 * Factor UI State Store (Zustand)
 * 只存储 UI 状态，不存储 filters（filters 由 URL search params 管理）
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Factor } from './types'
import { DEFAULT_VISIBLE_COLUMNS, FACTOR_COLUMNS } from './types'

// 默认列宽配置
const defaultColumnWidths: Record<string, number> = {}
FACTOR_COLUMNS.forEach((col) => {
  defaultColumnWidths[col.key] = col.width ?? 100
})

interface FactorUIState {
  // Selected factor for detail panel
  selectedFactor: Factor | null
  setSelectedFactor: (factor: Factor | null) => void

  // Detail panel visibility
  detailPanelOpen: boolean
  openDetailPanel: (factor: Factor) => void
  closeDetailPanel: () => void

  // View mode
  viewMode: 'table' | 'grid'
  setViewMode: (mode: 'table' | 'grid') => void

  // Selected factors for batch operations
  selectedFilenames: string[]
  toggleSelection: (filename: string) => void
  selectAll: (filenames: string[]) => void
  clearSelection: () => void

  // Edit mode
  editMode: boolean
  toggleEditMode: () => void

  // Table column configuration (persisted)
  visibleColumns: string[]
  setVisibleColumns: (columns: string[]) => void
  columnWidths: Record<string, number>
  setColumnWidth: (columnKey: string, width: number) => void
  resetColumnConfig: () => void
}

export const useFactorStore = create<FactorUIState>()(
  persist(
    (set) => ({
      // Selected factor
      selectedFactor: null,
      setSelectedFactor: (factor) => set({ selectedFactor: factor }),

      // Detail panel
      detailPanelOpen: false,
      openDetailPanel: (factor) => set({ selectedFactor: factor, detailPanelOpen: true }),
      closeDetailPanel: () => set({ detailPanelOpen: false }),

      // View mode
      viewMode: 'table',
      setViewMode: (mode) => set({ viewMode: mode }),

      // Selection
      selectedFilenames: [],
      toggleSelection: (filename) =>
        set((state) => ({
          selectedFilenames: state.selectedFilenames.includes(filename)
            ? state.selectedFilenames.filter((f) => f !== filename)
            : [...state.selectedFilenames, filename],
        })),
      selectAll: (filenames) => set({ selectedFilenames: filenames }),
      clearSelection: () => set({ selectedFilenames: [] }),

      // Edit mode
      editMode: false,
      toggleEditMode: () => set((state) => ({ editMode: !state.editMode })),

      // Table column configuration
      visibleColumns: [...DEFAULT_VISIBLE_COLUMNS],
      setVisibleColumns: (columns) => set({ visibleColumns: columns }),
      columnWidths: { ...defaultColumnWidths },
      setColumnWidth: (columnKey, width) =>
        set((state) => ({
          columnWidths: { ...state.columnWidths, [columnKey]: width },
        })),
      resetColumnConfig: () =>
        set({
          visibleColumns: [...DEFAULT_VISIBLE_COLUMNS],
          columnWidths: { ...defaultColumnWidths },
        }),
    }),
    {
      name: 'factor-ui-storage',
      // 只持久化部分状态
      partialize: (state) => ({
        viewMode: state.viewMode,
        visibleColumns: state.visibleColumns,
        columnWidths: state.columnWidths,
      }),
    }
  )
)

// 默认 filters 配置（供组件使用）
export const DEFAULT_FACTOR_FILTERS = {
  page: 1,
  page_size: 50,
  order_by: 'filename',
  excluded: 'active',
} as const
