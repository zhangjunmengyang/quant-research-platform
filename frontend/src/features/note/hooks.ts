/**
 * Note React Query Hooks
 */

import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { noteApi } from './api'
import type {
  NoteCreate,
  NoteUpdate,
  NoteListParams,
  ObservationCreate,
  HypothesisCreate,
  VerificationCreate,
  PromoteRequest,
  NoteType,
} from './types'

// Query Keys
export const noteKeys = {
  all: ['notes'] as const,
  lists: () => [...noteKeys.all, 'list'] as const,
  list: (params: NoteListParams) => [...noteKeys.lists(), params] as const,
  details: () => [...noteKeys.all, 'detail'] as const,
  detail: (id: number) => [...noteKeys.details(), id] as const,
  stats: () => [...noteKeys.all, 'stats'] as const,
  tags: () => [...noteKeys.all, 'tags'] as const,
  trails: () => [...noteKeys.all, 'trail'] as const,
  trail: (sessionId: string, includeArchived: boolean) =>
    [...noteKeys.trails(), sessionId, includeArchived] as const,
  verifications: (hypothesisId: number, includeArchived?: boolean) =>
    [...noteKeys.all, 'verifications', hypothesisId, includeArchived] as const,
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

// ==================== 研究记录相关 Hooks ====================

/**
 * Hook for recording notes (observation, hypothesis, verification)
 */
export function useRecordNote() {
  const queryClient = useQueryClient()

  const invalidateNotes = () => {
    queryClient.invalidateQueries({ queryKey: noteKeys.all })
  }

  const recordObservation = useMutation({
    mutationFn: (request: ObservationCreate) => noteApi.recordObservation(request),
    onSuccess: () => {
      invalidateNotes()
    },
  })

  const recordHypothesis = useMutation({
    mutationFn: (request: HypothesisCreate) => noteApi.recordHypothesis(request),
    onSuccess: () => {
      invalidateNotes()
    },
  })

  const recordVerification = useMutation({
    mutationFn: (request: VerificationCreate) => noteApi.recordVerification(request),
    onSuccess: () => {
      invalidateNotes()
    },
  })

  return {
    recordObservation,
    recordHypothesis,
    recordVerification,
  }
}

/**
 * Hook to record a specific type of note
 */
export function useRecordNoteByType(noteType: NoteType) {
  const { recordObservation, recordHypothesis, recordVerification } = useRecordNote()

  switch (noteType) {
    case 'observation':
      return recordObservation
    case 'hypothesis':
      return recordHypothesis
    case 'verification':
      return recordVerification
    default:
      return recordObservation
  }
}

/**
 * Hook to fetch research trail by session id
 */
export function useResearchTrail(sessionId: string | null, includeArchived = false) {
  return useQuery({
    queryKey: noteKeys.trail(sessionId ?? '', includeArchived),
    queryFn: () => noteApi.getResearchTrail(sessionId!, includeArchived),
    enabled: sessionId !== null && sessionId.length > 0,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * Hook to fetch verifications for a hypothesis
 *
 * 通过 Edge 系统获取关联到某个假设的所有验证笔记
 */
export function useVerifications(
  hypothesisId: number | null,
  includeArchived = false
) {
  return useQuery({
    queryKey: noteKeys.verifications(hypothesisId ?? 0, includeArchived),
    queryFn: () => noteApi.getVerifications(hypothesisId!, includeArchived),
    enabled: hypothesisId !== null && hypothesisId > 0,
    staleTime: DEFAULT_STALE_TIME,
  })
}

/**
 * @deprecated Use useVerifications instead
 * Hook to fetch notes linked to a specific note (legacy)
 */
export function useLinkedNotes(
  noteId: number | null,
  noteType?: string,
  includeArchived = false
) {
  // Redirect to verifications endpoint for hypothesis
  return useVerifications(noteId, includeArchived)
}

/**
 * Hook for archive/unarchive operations
 */
export function useNoteArchive() {
  const queryClient = useQueryClient()

  const invalidateNotes = () => {
    queryClient.invalidateQueries({ queryKey: noteKeys.all })
  }

  const archiveMutation = useMutation({
    mutationFn: (id: number) => noteApi.archive(id),
    onSuccess: (data) => {
      queryClient.setQueryData(noteKeys.detail(data.id), data)
      invalidateNotes()
    },
  })

  const unarchiveMutation = useMutation({
    mutationFn: (id: number) => noteApi.unarchive(id),
    onSuccess: (data) => {
      queryClient.setQueryData(noteKeys.detail(data.id), data)
      invalidateNotes()
    },
  })

  return {
    archive: archiveMutation,
    unarchive: unarchiveMutation,
  }
}

/**
 * Hook to promote note to experience
 */
export function usePromoteToExperience() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, request }: { id: number; request: PromoteRequest }) =>
      noteApi.promoteToExperience(id, request),
    onSuccess: (data) => {
      queryClient.setQueryData(noteKeys.detail(data.id), data)
      queryClient.invalidateQueries({ queryKey: noteKeys.all })
    },
  })
}
