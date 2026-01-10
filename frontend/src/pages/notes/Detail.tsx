/**
 * Note Detail Page
 * 笔记详情页 - 查看和编辑笔记
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate, Navigate } from 'react-router-dom'
import {
  ArrowLeft,
  Save,
  Trash2,
  Loader2,
  Calendar,
  Tag,
  Edit2,
  X,
} from 'lucide-react'
import { useNoteDetail, useNoteMutations } from '@/features/note'

export function Component() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const noteId = id ? parseInt(id, 10) : null
  const isNew = id === 'new'

  // Redirect /notes/new to list page (create via dialog now)
  if (isNew) {
    return <Navigate to="/notes" replace />
  }

  const { note, isLoading, isError, error } = useNoteDetail(noteId)
  const { updateNote, deleteNote } = useNoteMutations()

  const [isEditing, setIsEditing] = useState(false)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [tags, setTags] = useState('')

  // Sync form state with note data
  useEffect(() => {
    if (note) {
      setTitle(note.title)
      setContent(note.content)
      setTags(note.tags)
    }
  }, [note])

  const handleSave = async () => {
    if (!title.trim()) {
      alert('请输入标题')
      return
    }

    try {
      if (noteId) {
        await updateNote.mutateAsync({
          id: noteId,
          update: { title: title.trim(), content, tags },
        })
        setIsEditing(false)
      }
    } catch (err) {
      console.error('Save failed:', err)
      alert('保存失败')
    }
  }

  const handleDelete = async () => {
    if (!noteId) return
    if (confirm('确定要删除这条笔记吗?')) {
      await deleteNote.mutateAsync(noteId)
      navigate('/notes')
    }
  }

  const handleCancel = () => {
    setIsEditing(false)
    if (note) {
      setTitle(note.title)
      setContent(note.content)
      setTags(note.tags)
    }
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
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
        <button
          onClick={() => navigate('/notes')}
          className="mt-4 text-sm text-primary hover:underline"
        >
          返回列表
        </button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/notes')}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          返回列表
        </button>
        <div className="flex items-center gap-2">
          {isEditing ? (
            <>
              <button
                onClick={handleCancel}
                className="flex items-center gap-2 rounded-md border px-4 py-2 text-sm hover:bg-muted"
              >
                <X className="h-4 w-4" />
                取消
              </button>
              <button
                onClick={handleSave}
                disabled={updateNote.isPending}
                className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {updateNote.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                保存
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-2 rounded-md border px-4 py-2 text-sm hover:bg-muted"
              >
                <Edit2 className="h-4 w-4" />
                编辑
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteNote.isPending}
                className="flex items-center gap-2 rounded-md border border-destructive px-4 py-2 text-sm text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="h-4 w-4" />
                删除
              </button>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="rounded-lg border bg-card p-6">
        {isEditing ? (
          <div className="space-y-4">
            {/* Title */}
            <div>
              <label className="mb-1 block text-sm font-medium">标题</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="输入笔记标题..."
                className="w-full rounded-md border bg-background px-4 py-2 text-lg font-medium focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Tags */}
            <div>
              <label className="mb-1 block text-sm font-medium">标签</label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="输入标签，用逗号分隔..."
                className="w-full rounded-md border bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Content */}
            <div>
              <label className="mb-1 block text-sm font-medium">内容 (支持 Markdown)</label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="输入笔记内容..."
                rows={20}
                className="w-full resize-none rounded-md border bg-background px-4 py-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
        ) : (
          <div>
            {/* Title */}
            <h1 className="text-2xl font-bold">{note?.title}</h1>

            {/* Meta */}
            <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              {note?.tags && (
                <div className="flex items-center gap-1">
                  <Tag className="h-4 w-4" />
                  <span>{note.tags}</span>
                </div>
              )}
              <div className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                <span>更新于 {formatDate(note?.updated_at)}</span>
              </div>
            </div>

            {/* Content */}
            <div className="mt-6">
              {note?.content ? (
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                  {note.content}
                </pre>
              ) : (
                <p className="text-muted-foreground">(空内容)</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
