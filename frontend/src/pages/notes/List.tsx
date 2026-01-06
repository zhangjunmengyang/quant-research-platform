/**
 * Notes List Page
 * 笔记列表页 - 展示所有经验笔记
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText,
  Plus,
  Search,
  Loader2,
  Tag,
  Calendar,
  Trash2,
  Save,
} from 'lucide-react'
import { useNotes, useNoteMutations, useNoteTags } from '@/features/note'
import type { Note, NoteListParams } from '@/features/note'
import { cn } from '@/lib/utils'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'

export function Component() {
  const navigate = useNavigate()
  const [params, setParams] = useState<NoteListParams>({ page: 1, page_size: 20 })
  const [searchInput, setSearchInput] = useState('')
  const { data, isLoading, isError, error } = useNotes(params)
  const { data: tags = [] } = useNoteTags()
  const { createNote, deleteNote } = useNoteMutations()

  // Dialog state for creating new note
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newTags, setNewTags] = useState('')
  const [newContent, setNewContent] = useState('')

  const handleOpenDialog = () => {
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
      await createNote.mutateAsync({
        title: newTitle.trim(),
        content: newContent,
        tags: newTags,
        source: 'manual',
      })
      handleCloseDialog()
    } catch (err) {
      console.error('Create note failed:', err)
      alert('创建失败')
    }
  }

  const handleSearch = () => {
    setParams({ ...params, search: searchInput, page: 1 })
  }

  const handleTagFilter = (tag: string) => {
    setParams({ ...params, tags: tag, page: 1 })
  }

  const handleClearFilter = () => {
    setParams({ page: 1, page_size: 20 })
    setSearchInput('')
  }

  const handleDelete = async (e: React.MouseEvent, note: Note) => {
    e.stopPropagation()
    if (confirm(`确定要删除笔记「${note.title}」吗?`)) {
      await deleteNote.mutateAsync(note.id)
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
          <h1 className="text-2xl font-bold">经验笔记</h1>
          <p className="text-muted-foreground">
            共 {data?.total ?? 0} 条笔记
          </p>
        </div>
        <button
          onClick={handleOpenDialog}
          className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          新建笔记
        </button>
      </div>

      {/* Search and Filter */}
      <div className="flex flex-wrap gap-4">
        <div className="flex flex-1 gap-2">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="搜索笔记..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full rounded-md border bg-background py-2 pl-10 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <button
            onClick={handleSearch}
            className="rounded-md bg-secondary px-4 py-2 text-sm hover:bg-secondary/80"
          >
            搜索
          </button>
          {(params.search || params.tags) && (
            <button
              onClick={handleClearFilter}
              className="rounded-md border px-4 py-2 text-sm hover:bg-muted"
            >
              清除筛选
            </button>
          )}
        </div>
      </div>

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => (
            <button
              key={tag}
              onClick={() => handleTagFilter(tag)}
              className={cn(
                'rounded-full px-3 py-1 text-xs border transition-colors',
                params.tags === tag
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'hover:bg-muted'
              )}
            >
              {tag}
            </button>
          ))}
        </div>
      )}

      {/* Notes List */}
      <div className="space-y-4">
        {data?.items.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center rounded-lg border border-dashed">
            <FileText className="h-12 w-12 text-muted-foreground/50" />
            <p className="mt-4 text-muted-foreground">
              {params.search || params.tags ? '没有匹配的笔记' : '还没有笔记'}
            </p>
            <button
              onClick={handleOpenDialog}
              className="mt-4 flex items-center gap-2 text-sm text-primary hover:underline"
            >
              <Plus className="h-4 w-4" />
              创建第一条笔记
            </button>
          </div>
        ) : (
          data?.items.map((note) => (
            <div
              key={note.id}
              onClick={() => navigate(`/notes/${note.id}`)}
              className="group cursor-pointer rounded-lg border p-4 transition-colors hover:bg-muted/50"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
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
                <button
                  onClick={(e) => handleDelete(e, note)}
                  className="ml-4 rounded p-2 opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                  title="删除"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setParams({ ...params, page: (params.page ?? 1) - 1 })}
            disabled={!data.has_prev}
            className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
          >
            上一页
          </button>
          <span className="text-sm text-muted-foreground">
            第 {data.page} / {data.total_pages} 页
          </span>
          <button
            onClick={() => setParams({ ...params, page: (params.page ?? 1) + 1 })}
            disabled={!data.has_next}
            className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
          >
            下一页
          </button>
        </div>
      )}

      {/* Create Note Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>新建笔记</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="mb-1 block text-sm font-medium">标题</label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="输入笔记标题..."
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
                placeholder="输入笔记内容..."
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
              disabled={createNote.isPending}
              className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {createNote.isPending ? (
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
