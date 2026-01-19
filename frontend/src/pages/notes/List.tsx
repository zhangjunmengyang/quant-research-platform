/**
 * Notes List Page
 * 笔记列表页 - 展示所有经验概览
 */

import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText,
  Plus,
  Loader2,
  Tag,
  Calendar,
  Trash2,
  Save,
  Eye,
  Lightbulb,
  FlaskConical,
  Archive,
  ArchiveRestore,
  Star,
  ChevronDown,
} from 'lucide-react'
import {
  useNotes,
  useNoteMutations,
  useNoteTags,
  useRecordNote,
  useNoteArchive,
  NoteType,
  NOTE_TYPE_LABELS,
  NOTE_TYPE_COLORS,
} from '@/features/note'
import type { Note, NoteListParams } from '@/features/note'
import { cn } from '@/lib/utils'
import { FilterToolbar } from '@/components/ui/filter-toolbar'
import { FilterSelect, type SelectOption } from '@/components/ui/filter-select'
import { Pagination } from '@/components/ui/pagination'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const DEFAULT_FILTERS: NoteListParams = {
  page: 1,
  page_size: 20,
  is_archived: false,
}

// 归档状态筛选选项
type ArchiveFilter = 'active' | 'archived' | 'all'

const ARCHIVE_FILTER_OPTIONS: SelectOption[] = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '活跃笔记' },
  { value: 'archived', label: '已归档' },
]

// 笔记类型筛选选项
const NOTE_TYPE_OPTIONS: SelectOption[] = [
  { value: '', label: '全部类型' },
  ...Object.values(NoteType).map((type) => ({
    value: type,
    label: NOTE_TYPE_LABELS[type],
  })),
]

// 快速记录类型配置
const QUICK_RECORD_TYPES = [
  {
    type: NoteType.OBSERVATION,
    label: '记录观察',
    icon: Eye,
    description: '对数据或现象的客观记录',
  },
  {
    type: NoteType.HYPOTHESIS,
    label: '记录假设',
    icon: Lightbulb,
    description: '基于观察提出的待验证假设',
  },
  {
    type: NoteType.FINDING,
    label: '记录发现',
    icon: FlaskConical,
    description: '验证后的结论或发现',
  },
]

export function Component() {
  const navigate = useNavigate()
  const [filters, setFilters] = useState<NoteListParams>(DEFAULT_FILTERS)
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [archiveFilter, setArchiveFilter] = useState<ArchiveFilter>('active')

  const queryParams = useMemo(
    () => ({
      ...filters,
      search: searchQuery || undefined,
      is_archived: archiveFilter === undefined ? false : archiveFilter === 'archived',
    }),
    [filters, searchQuery, archiveFilter]
  )

  const { data, isLoading, isError, error } = useNotes(queryParams)
  const { data: tags = [] } = useNoteTags()
  const { createNote, deleteNote } = useNoteMutations()
  const { recordObservation, recordHypothesis, recordFinding } = useRecordNote()
  const { archive, unarchive } = useNoteArchive()

  // Dialog state for creating new note
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [dialogType, setDialogType] = useState<NoteType>(NoteType.GENERAL)
  const [newTitle, setNewTitle] = useState('')
  const [newTags, setNewTags] = useState('')
  const [newContent, setNewContent] = useState('')

  // 动态生成标签选项
  const tagOptions: SelectOption[] = useMemo(
    () => [
      { value: '', label: '全部标签' },
      ...tags.map((tag) => ({ value: tag, label: tag })),
    ],
    [tags]
  )

  const handleOpenDialog = (type: NoteType = NoteType.GENERAL) => {
    setDialogType(type)
    setNewTitle('')
    setNewTags('')
    setNewContent('')
    setIsDialogOpen(true)
  }

  const handleCloseDialog = () => {
    setIsDialogOpen(false)
    setNewTitle('')
    setNewTags('')
    setNewContent('')
  }

  const handleCreateNote = async () => {
    if (!newTitle.trim()) {
      alert('请输入标题')
      return
    }

    try {
      const noteData = {
        title: newTitle.trim(),
        content: newContent,
        tags: newTags,
        source: 'manual',
      }

      // 根据类型调用不同的 API
      switch (dialogType) {
        case NoteType.OBSERVATION:
          await recordObservation.mutateAsync(noteData)
          break
        case NoteType.HYPOTHESIS:
          await recordHypothesis.mutateAsync(noteData)
          break
        case NoteType.FINDING:
          await recordFinding.mutateAsync(noteData)
          break
        default:
          await createNote.mutateAsync({
            ...noteData,
            note_type: dialogType,
          })
      }
      handleCloseDialog()
    } catch (err) {
      console.error('Create note failed:', err)
      alert('创建失败')
    }
  }

  const handleSearch = () => {
    setSearchQuery(searchInput)
    setFilters((prev) => ({ ...prev, page: 1 }))
  }

  const handleSearchInputChange = (value: string) => {
    setSearchInput(value)
    if (value === '') {
      setSearchQuery('')
    }
  }

  const handleTagFilter = (tag: string | undefined) => {
    setFilters((prev) => ({ ...prev, tags: tag, page: 1 }))
  }

  const handleNoteTypeFilter = (noteType: string | undefined) => {
    setFilters((prev) => ({ ...prev, note_type: noteType as NoteType | undefined, page: 1 }))
  }

  const handleArchiveFilterChange = (filter: string | undefined) => {
    const value = filter as ArchiveFilter | undefined
    setArchiveFilter(value ?? 'active')
    setFilters((prev) => ({ ...prev, page: 1 }))
  }

  const handleResetFilters = () => {
    setFilters(DEFAULT_FILTERS)
    setSearchQuery('')
    setSearchInput('')
    setArchiveFilter('active')
  }

  const handlePageChange = (page: number) => {
    setFilters((prev) => ({ ...prev, page }))
  }

  const handleDelete = async (e: React.MouseEvent, note: Note) => {
    e.stopPropagation()
    if (confirm(`确定要删除笔记"${note.title}"吗?`)) {
      await deleteNote.mutateAsync(note.id)
    }
  }

  const handleArchiveToggle = async (e: React.MouseEvent, note: Note) => {
    e.stopPropagation()
    if (note.is_archived) {
      await unarchive.mutateAsync(note.id)
    } else {
      await archive.mutateAsync(note.id)
    }
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
  }

  const isCreating =
    createNote.isPending ||
    recordObservation.isPending ||
    recordHypothesis.isPending ||
    recordFinding.isPending

  const hasActiveFilters = !!(
    searchQuery ||
    filters.tags ||
    filters.note_type ||
    archiveFilter !== 'active'
  )

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-destructive">
        <p>加载失败</p>
        <p className="text-sm">{(error as Error)?.message}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">经验概览</h1>
          <p className="text-muted-foreground">
            共 {data?.total ?? 0} 条笔记
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* 快速记录下拉菜单 */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted">
                快速记录
                <ChevronDown className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              {QUICK_RECORD_TYPES.map((item) => {
                const Icon = item.icon
                const colors = NOTE_TYPE_COLORS[item.type]
                return (
                  <DropdownMenuItem
                    key={item.type}
                    onClick={() => handleOpenDialog(item.type)}
                    className="flex flex-col items-start gap-1 py-3"
                  >
                    <div className="flex items-center gap-2">
                      <div className={cn('rounded p-1', colors.bg)}>
                        <Icon className={cn('h-4 w-4', colors.text)} />
                      </div>
                      <span className="font-medium">{item.label}</span>
                    </div>
                    <span className="text-xs text-muted-foreground pl-7">
                      {item.description}
                    </span>
                  </DropdownMenuItem>
                )
              })}
            </DropdownMenuContent>
          </DropdownMenu>

          <button
            onClick={() => handleOpenDialog(NoteType.GENERAL)}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            新建笔记
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <FilterToolbar
        searchValue={searchInput}
        onSearchChange={handleSearchInputChange}
        onSearch={handleSearch}
        searchPlaceholder="搜索笔记..."
        hasActiveFilters={hasActiveFilters}
        onReset={handleResetFilters}
      >
        <FilterSelect
          label="类型"
          options={NOTE_TYPE_OPTIONS}
          value={filters.note_type}
          onChange={handleNoteTypeFilter}
        />
        <FilterSelect
          label="状态"
          options={ARCHIVE_FILTER_OPTIONS}
          value={archiveFilter}
          onChange={handleArchiveFilterChange}
        />
        {tags.length > 0 && (
          <FilterSelect
            label="标签"
            options={tagOptions}
            value={filters.tags}
            onChange={handleTagFilter}
          />
        )}
      </FilterToolbar>

      {/* Notes List */}
      <div className="space-y-4">
        {data?.items.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center rounded-lg border border-dashed">
            <FileText className="h-12 w-12 text-muted-foreground/50" />
            <p className="mt-4 text-muted-foreground">
              {hasActiveFilters ? '没有匹配的笔记' : '还没有笔记'}
            </p>
            <button
              onClick={() => handleOpenDialog(NoteType.GENERAL)}
              className="mt-4 flex items-center gap-2 text-sm text-primary hover:underline"
            >
              <Plus className="h-4 w-4" />
              创建第一条笔记
            </button>
          </div>
        ) : (
          data?.items.map((note) => {
            const typeColors = NOTE_TYPE_COLORS[note.note_type] || NOTE_TYPE_COLORS[NoteType.GENERAL]
            return (
              <div
                key={note.id}
                onClick={() => navigate(`/notes/${note.id}`)}
                className={cn(
                  'group cursor-pointer rounded-lg border bg-card p-4 transition-colors hover:bg-muted/30',
                  note.is_archived && 'opacity-60'
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {/* 笔记类型标签 */}
                      <span
                        className={cn(
                          'inline-flex items-center rounded px-2 py-0.5 text-xs border',
                          typeColors.bg,
                          typeColors.text,
                          typeColors.border
                        )}
                      >
                        {NOTE_TYPE_LABELS[note.note_type] || NOTE_TYPE_LABELS[NoteType.GENERAL]}
                      </span>
                      {/* 已提炼为经验标记 */}
                      {note.promoted_to_experience_id && (
                        <span className="inline-flex items-center gap-1 rounded bg-yellow-50 px-2 py-0.5 text-xs text-yellow-700 border border-yellow-200">
                          <Star className="h-3 w-3" />
                          已提炼
                        </span>
                      )}
                      {/* 归档标记 */}
                      {note.is_archived && (
                        <span className="inline-flex items-center gap-1 rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                          <Archive className="h-3 w-3" />
                          已归档
                        </span>
                      )}
                    </div>
                    <h3 className="font-medium truncate">{note.title}</h3>
                    <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                      {note.content?.slice(0, 200) || '(空内容)'}
                    </p>
                    <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                      {note.tags && (
                        <div className="flex items-center gap-1">
                          <Tag className="h-3 w-3" />
                          <span>{note.tags}</span>
                        </div>
                      )}
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        <span>{formatDate(note.updated_at)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="ml-4 flex items-center gap-1">
                    {/* 归档/取消归档按钮 */}
                    <button
                      onClick={(e) => handleArchiveToggle(e, note)}
                      className="rounded p-2 opacity-0 transition-opacity hover:bg-muted group-hover:opacity-100"
                      title={note.is_archived ? '取消归档' : '归档'}
                    >
                      {note.is_archived ? (
                        <ArchiveRestore className="h-4 w-4" />
                      ) : (
                        <Archive className="h-4 w-4" />
                      )}
                    </button>
                    {/* 删除按钮 */}
                    <button
                      onClick={(e) => handleDelete(e, note)}
                      className="rounded p-2 opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                      title="删除"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <Pagination
          page={data.page}
          pageSize={data.page_size}
          total={data.total}
          totalPages={data.total_pages}
          onPageChange={handlePageChange}
          position="center"
        />
      )}

      {/* Create Note Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {dialogType !== NoteType.GENERAL && (
                <span
                  className={cn(
                    'inline-flex items-center rounded px-2 py-0.5 text-sm border',
                    NOTE_TYPE_COLORS[dialogType].bg,
                    NOTE_TYPE_COLORS[dialogType].text,
                    NOTE_TYPE_COLORS[dialogType].border
                  )}
                >
                  {NOTE_TYPE_LABELS[dialogType]}
                </span>
              )}
              {dialogType === NoteType.GENERAL ? '新建笔记' : `记录${NOTE_TYPE_LABELS[dialogType]}`}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="mb-1 block text-sm font-medium">标题</label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder={`输入${NOTE_TYPE_LABELS[dialogType]}标题...`}
                className="w-full rounded-md border bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                autoFocus
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">标签</label>
              <input
                type="text"
                value={newTags}
                onChange={(e) => setNewTags(e.target.value)}
                placeholder="输入标签，用逗号分隔..."
                className="w-full rounded-md border bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">内容 (支持 Markdown)</label>
              <textarea
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                placeholder={`输入${NOTE_TYPE_LABELS[dialogType]}内容...`}
                rows={10}
                className="w-full resize-none rounded-md border bg-background px-4 py-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
          <DialogFooter>
            <button
              onClick={handleCloseDialog}
              className="rounded-md border px-4 py-2 text-sm hover:bg-muted"
            >
              取消
            </button>
            <button
              onClick={handleCreateNote}
              disabled={isCreating}
              className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {isCreating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              保存
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
