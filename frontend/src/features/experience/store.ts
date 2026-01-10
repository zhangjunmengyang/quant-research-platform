/**
 * Experience UI State Store (Zustand)
 * 只管理 UI 相关状态，筛选状态由页面组件管理（支持 URL params）
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Experience } from './types'

interface ExperienceUIState {
  // Selected experience for detail panel
  selectedExperience: Experience | null
  setSelectedExperience: (experience: Experience | null) => void

  // Detail panel visibility
  detailPanelOpen: boolean
  openDetailPanel: (experience: Experience) => void
  closeDetailPanel: () => void

  // View mode（持久化）
  viewMode: 'list' | 'grid'
  setViewMode: (mode: 'list' | 'grid') => void

  // Selected experiences for batch operations
  selectedIds: number[]
  toggleSelection: (id: number) => void
  selectAll: (ids: number[]) => void
  clearSelection: () => void
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
      // 只持久化 viewMode
      partialize: (state) => ({
        viewMode: state.viewMode,
      }),
    }
  )
)
