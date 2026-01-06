/**
 * Note React Query Hooks
 */

import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { noteApi } from './api'
import type { NoteCreate, NoteUpdate, NoteListParams } from './types'

// Query Keys
export const noteKeys = {
  all: ['notes'] as const,
  lists: () => [...noteKeys.all, 'list'] as const,
  list: (params: NoteListParams) => [...noteKeys.lists(), params] as const,
  details: () => [...noteKeys.all, 'detail'] as const,
  detail: (id: number) => [...noteKeys.details(), id] as const,
  stats: () => [...noteKeys.all, 'stats'] as const,
  tags: () => [...noteKeys.all, 'tags'] as const,
}

// 默认缓存时间: 5 分钟
const DEFAULT_STALE_TIME = 5 * 60 * 1000

/**
 * Hook to fetch paginated note list
 */
export function useNotes(params: NoteListParams = {}) {
  return useQuery({
    queryKey: noteKeys.list(params),
    queryFn: () => noteApi.list(params),
    placeholderData: keepPreviousData,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch a single note by id
 */
export function useNote(id: number | null) {
  return useQuery({
    queryKey: noteKeys.detail(id ?? 0),
    queryFn: () => noteApi.get(id!),
    enabled: id !== null && id > 0,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch note statistics
 */
export function useNoteStats() {
  return useQuery({
    queryKey: noteKeys.stats(),
    queryFn: noteApi.getStats,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch available tags
 */
export function useNoteTags() {
  return useQuery({
    queryKey: noteKeys.tags(),
    queryFn: noteApi.getTags,
    staleTime: 10 * 60 * 1000, // 标签列表很少变化，缓存 10 分钟
  })
}

/**
 * Hook for note mutations (create, update, delete)
 */
export function useNoteMutations() {
  const queryClient = useQueryClient()

  const invalidateNotes = () => {
    queryClient.invalidateQueries({ queryKey: noteKeys.all })
  }

  const createMutation = useMutation({
    mutationFn: (note: NoteCreate) => noteApi.create(note),
    onSuccess: () => {
      invalidateNotes()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, update }: { id: number; update: NoteUpdate }) =>
      noteApi.update(id, update),
    onSuccess: (data) => {
      queryClient.setQueryData(noteKeys.detail(data.id), data)
      invalidateNotes()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => noteApi.delete(id),
    onSuccess: () => {
      invalidateNotes()
    },
  })

  return {
    createNote: createMutation,
    updateNote: updateMutation,
    deleteNote: deleteMutation,
  }
}

/**
 * Hook to get note by id with refetch capability
 */
export function useNoteDetail(id: number | null) {
  const query = useNote(id)
  const mutations = useNoteMutations()

  return {
    note: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    ...mutations,
  }
}
