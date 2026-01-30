/**
 * Experience React Query Hooks
 * 简化版本: 移除 validate/deprecate/curate，以标签为核心管理
 */

import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { experienceApi } from './api'
import type {
  ExperienceCreate,
  ExperienceUpdate,
  ExperienceListParams,
  ExperienceQueryParams,
} from './types'

// Query Keys
export const experienceKeys = {
  all: ['experiences'] as const,
  lists: () => [...experienceKeys.all, 'list'] as const,
  list: (params: ExperienceListParams) => [...experienceKeys.lists(), params] as const,
  details: () => [...experienceKeys.all, 'detail'] as const,
  detail: (id: number) => [...experienceKeys.details(), id] as const,
  stats: () => [...experienceKeys.all, 'stats'] as const,
  query: (params: ExperienceQueryParams) => [...experienceKeys.all, 'query', params] as const,
}

// 默认缓存时间: 5 分钟
const DEFAULT_STALE_TIME = 5 * 60 * 1000

/**
 * Hook to fetch paginated experience list
 */
export function useExperiences(params: ExperienceListParams = {}) {
  return useQuery({
    queryKey: experienceKeys.list(params),
    queryFn: () => experienceApi.list(params),
    placeholderData: keepPreviousData,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch a single experience by id
 */
export function useExperience(id: number | null) {
  return useQuery({
    queryKey: experienceKeys.detail(id ?? 0),
    queryFn: () => experienceApi.get(id!),
    enabled: id !== null && id > 0,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch experience statistics
 */
export function useExperienceStats() {
  return useQuery({
    queryKey: experienceKeys.stats(),
    queryFn: experienceApi.getStats,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook for experience mutations (create, update, delete)
 */
export function useExperienceMutations() {
  const queryClient = useQueryClient()

  const invalidateExperiences = () => {
    queryClient.invalidateQueries({ queryKey: experienceKeys.all })
  }

  const invalidateListAndStats = () => {
    queryClient.invalidateQueries({ queryKey: experienceKeys.lists() })
    queryClient.invalidateQueries({ queryKey: experienceKeys.stats() })
  }

  const createMutation = useMutation({
    mutationFn: (experience: ExperienceCreate) => experienceApi.create(experience),
    onSuccess: () => {
      invalidateExperiences()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, update }: { id: number; update: ExperienceUpdate }) =>
      experienceApi.update(id, update),
    onSuccess: (data) => {
      queryClient.setQueryData(experienceKeys.detail(data.id), data)
      invalidateListAndStats()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => experienceApi.delete(id),
    onSuccess: () => {
      invalidateExperiences()
    },
  })

  return {
    createExperience: createMutation,
    updateExperience: updateMutation,
    deleteExperience: deleteMutation,
  }
}

/**
 * Hook for semantic query experiences
 */
export function useExperienceQuery() {
  return useMutation({
    mutationFn: (params: ExperienceQueryParams) => experienceApi.query(params),
  })
}

/**
 * Hook to get experience by id with refetch capability
 */
export function useExperienceDetail(id: number | null) {
  const query = useExperience(id)
  const mutations = useExperienceMutations()

  return {
    experience: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    ...mutations,
  }
}
