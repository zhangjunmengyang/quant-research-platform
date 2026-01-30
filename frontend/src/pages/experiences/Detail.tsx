/**
 * Experience Detail Page
 * 经验详情页 - 查看和编辑经验
 */

import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Navigate, useLocation } from 'react-router-dom'
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
import { useExperienceDetail } from '@/features/experience'
import type { ExperienceContent, ExperienceContext } from '@/features/experience'
import { EntityGraph, RelationEditor } from '@/features/graph'

export function Component() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const experienceId = id ? parseInt(id, 10) : null
  const isNew = id === 'new'

  // 安全的后退函数：如果没有历史记录则返回列表页
  const handleBack = useCallback(() => {
    if (location.key === 'default') {
      navigate('/experiences', { replace: true })
    } else {
      navigate(-1)
    }
  }, [navigate, location.key])

  // Redirect /experiences/new to list page (create via dialog now)
  if (isNew) {
    return <Navigate to="/experiences" replace />
  }

  const {
    experience,
    isLoading,
    isError,
    error,
    updateExperience,
    deleteExperience,
  } = useExperienceDetail(experienceId)

  const [isEditing, setIsEditing] = useState(false)
  const [title, setTitle] = useState('')
  const [problem, setProblem] = useState('')
  const [approach, setApproach] = useState('')
  const [result, setResult] = useState('')
  const [lesson, setLesson] = useState('')
  const [tags, setTags] = useState('')

  // Sync form state with experience data
  useEffect(() => {
    if (experience) {
      setTitle(experience.title)
      setProblem(experience.content?.problem || '')
      setApproach(experience.content?.approach || '')
      setResult(experience.content?.result || '')
      setLesson(experience.content?.lesson || '')
      setTags(experience.context?.tags?.join(', ') || '')
    }
  }, [experience])

  const handleSave = async () => {
    if (!title.trim()) {
      alert('请输入标题')
      return
    }

    try {
      if (experienceId) {
        const content: ExperienceContent = {
          problem: problem.trim(),
          approach: approach.trim(),
          result: result.trim(),
          lesson: lesson.trim(),
        }
        const context: ExperienceContext = {
          tags: tags.split(',').map(t => t.trim()).filter(Boolean),
        }
        await updateExperience.mutateAsync({
          id: experienceId,
          update: { title: title.trim(), content, context },
        })
        setIsEditing(false)
      }
    } catch (err) {
      console.error('Save failed:', err)
      alert('保存失败')
    }
  }

  const handleDelete = async () => {
    if (!experienceId) return
    if (confirm('确定要删除这条经验吗?')) {
      await deleteExperience.mutateAsync(experienceId)
      navigate('/experiences')
    }
  }

  const handleCancel = () => {
    setIsEditing(false)
    if (experience) {
      setTitle(experience.title)
      setProblem(experience.content?.problem || '')
      setApproach(experience.content?.approach || '')
      setResult(experience.content?.result || '')
      setLesson(experience.content?.lesson || '')
      setTags(experience.context?.tags?.join(', ') || '')
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
          onClick={handleBack}
          className="mt-4 text-sm text-primary hover:underline"
        >
          返回
        </button>
      </div>
    )
  }

  const expTags = experience?.context?.tags || []

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={handleBack}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          返回
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
                disabled={updateExperience.isPending}
                className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {updateExperience.isPending ? (
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
                disabled={deleteExperience.isPending}
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
                placeholder="输入经验标题..."
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

            {/* PARL Content */}
            <div className="space-y-4 pt-4">
              <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
                PARL 框架
              </h3>

              <div>
                <label className="mb-1 block text-sm font-medium">Problem (问题)</label>
                <textarea
                  value={problem}
                  onChange={(e) => setProblem(e.target.value)}
                  placeholder="面临的问题或挑战..."
                  rows={4}
                  className="w-full resize-none rounded-md border bg-background px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">Approach (方法)</label>
                <textarea
                  value={approach}
                  onChange={(e) => setApproach(e.target.value)}
                  placeholder="采用的方法或策略..."
                  rows={4}
                  className="w-full resize-none rounded-md border bg-background px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">Result (结果)</label>
                <textarea
                  value={result}
                  onChange={(e) => setResult(e.target.value)}
                  placeholder="得到的结果..."
                  rows={4}
                  className="w-full resize-none rounded-md border bg-background px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">Lesson (教训)</label>
                <textarea
                  value={lesson}
                  onChange={(e) => setLesson(e.target.value)}
                  placeholder="总结的教训或规律..."
                  rows={4}
                  className="w-full resize-none rounded-md border bg-background px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
          </div>
        ) : (
          <div>
            {/* Title */}
            <h1 className="text-2xl font-bold">{experience?.title}</h1>

            {/* Meta */}
            <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              {expTags.length > 0 && (
                <div className="flex items-center gap-1">
                  <Tag className="h-4 w-4" />
                  <span>{expTags.join(', ')}</span>
                </div>
              )}
              <div className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                <span>更新于 {formatDate(experience?.updated_at)}</span>
              </div>
            </div>

            {/* PARL Content */}
            <div className="mt-6 space-y-4">
              {experience?.content?.problem && (
                <div className="rounded-lg border p-4">
                  <div className="text-xs font-medium text-muted-foreground mb-2">Problem (问题)</div>
                  <p className="text-sm whitespace-pre-wrap">{experience.content.problem}</p>
                </div>
              )}

              {experience?.content?.approach && (
                <div className="rounded-lg border p-4">
                  <div className="text-xs font-medium text-muted-foreground mb-2">Approach (方法)</div>
                  <p className="text-sm whitespace-pre-wrap">{experience.content.approach}</p>
                </div>
              )}

              {experience?.content?.result && (
                <div className="rounded-lg border p-4">
                  <div className="text-xs font-medium text-muted-foreground mb-2">Result (结果)</div>
                  <p className="text-sm whitespace-pre-wrap">{experience.content.result}</p>
                </div>
              )}

              {experience?.content?.lesson && (
                <div className="rounded-lg border p-4 bg-primary/5 border-primary/20">
                  <div className="text-xs font-medium text-primary mb-2">Lesson (教训)</div>
                  <p className="text-sm whitespace-pre-wrap">{experience.content.lesson}</p>
                </div>
              )}

              {!experience?.content?.problem &&
                !experience?.content?.approach &&
                !experience?.content?.result &&
                !experience?.content?.lesson && (
                  <p className="text-muted-foreground">(空内容)</p>
                )}
            </div>
          </div>
        )}
      </div>

      {/* 知识关联图 */}
      {experience?.uuid && (
        <div className="rounded-lg border bg-card p-6">
          <EntityGraph
            entityType="experience"
            entityId={experience.uuid}
            entityName={experience.title}
            height={200}
          />
        </div>
      )}

      {/* 关联管理 */}
      {experience?.uuid && (
        <div className="rounded-lg border bg-card p-6">
          <RelationEditor
            entityType="experience"
            entityId={experience.uuid}
          />
        </div>
      )}
    </div>
  )
}
