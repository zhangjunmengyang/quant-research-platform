/**
 * Experience UI State Store (Zustand)
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Experience, ExperienceListParams, ExperienceLevel, ExperienceStatus } from './types'

interface ExperienceUIState {
  // Selected experience for detail panel
  selectedExperience: Experience | null
  setSelectedExperience: (experience: Experience | null) => void

  // Detail panel visibility
  detailPanelOpen: boolean
  openDetailPanel: (experience: Experience) => void
  closeDetailPanel: () => void

  // List filters
  filters: ExperienceListParams
  setFilters: (filters: Partial<ExperienceListParams>) => void
  resetFilters: () => void

  // View mode
  viewMode: 'list' | 'grid'
  setViewMode: (mode: 'list' | 'grid') => void

  // Selected experiences for batch operations
  selectedIds: number[]
  toggleSelection: (id: number) => void
  selectAll: (ids: number[]) => void
  clearSelection: () => void
}

const defaultFilters: ExperienceListParams = {
  page: 1,
  page_size: 20,
  order_by: 'updated_at',
  order_desc: true,
  include_deprecated: false,
}

export const useExperienceStore = create<ExperienceUIState>()(
  persist(
    (set) => ({
      // Selected experience
      selectedExperience: null,
      setSelectedExperience: (experience) => set({ selectedExperience: experience }),

      // Detail panel
      detailPanelOpen: false,
      openDetailPanel: (experience) =>
        set({ selectedExperience: experience, detailPanelOpen: true }),
      closeDetailPanel: () => set({ detailPanelOpen: false }),

      // Filters
      filters: defaultFilters,
      setFilters: (newFilters) =>
        set((state) => ({
          filters: { ...state.filters, ...newFilters },
        })),
      resetFilters: () => set({ filters: defaultFilters }),

      // View mode
      viewMode: 'list',
      setViewMode: (mode) => set({ viewMode: mode }),

      // Selection
      selectedIds: [],
      toggleSelection: (id) =>
        set((state) => ({
          selectedIds: state.selectedIds.includes(id)
            ? state.selectedIds.filter((i) => i !== id)
            : [...state.selectedIds, id],
        })),
      selectAll: (ids) => set({ selectedIds: ids }),
      clearSelection: () => set({ selectedIds: [] }),
    }),
    {
      name: 'experience-ui-storage',
      // 只持久化部分状态
      partialize: (state) => ({
        viewMode: state.viewMode,
        filters: {
          page_size: state.filters.page_size,
          order_by: state.filters.order_by,
          order_desc: state.filters.order_desc,
        },
      }),
    }
  )
)
