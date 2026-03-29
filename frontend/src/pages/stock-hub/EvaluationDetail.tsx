/**
 * Stock Hub - 因子评估详情页
 *
 * 查看/编辑已保存的因子评估记录。
 */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, Trash2, Loader2, Edit3, Tag } from 'lucide-react'
import { stockApi } from '@/features/stock-hub'
import type { FactorEvaluationItem } from '@/features/stock-hub'

const EVAL_TYPE_LABELS: Record<string, string> = {
  comprehensive: '综合评估',
  ic_performance: 'IC表现',
  grouping_ability: '分组能力',
  style_profile: '风格画像',
  market_cap: '市值分析',
}

export function Component() {
  const { t } = useTranslation()
  const { uuid } = useParams<{ uuid: string }>()
  const navigate = useNavigate()

  const [data, setData] = useState<FactorEvaluationItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Editable fields
  const [title, setTitle] = useState('')
  const [evaluations, setEvaluations] = useState<Record<string, string>>({})
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')

  // UI state
  const [editingTitle, setEditingTitle] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())
  const [edited, setEdited] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)

  // Fetch data
  useEffect(() => {
    if (!uuid) return
    setLoading(true)
    setError(null)
    stockApi
      .getEvaluation(uuid)
      .then((item) => {
        setData(item)
        setTitle(item.title)
        setEvaluations({ ...item.evaluations })
        setTags([...item.tags])
        // Auto-expand all sections
        setExpandedSections(new Set(Object.keys(item.evaluations)))
      })
      .catch((err) => {
        setError(err?.message || 'Failed to load evaluation')
      })
      .finally(() => setLoading(false))
  }, [uuid])

  const markEdited = useCallback(() => setEdited(true), [])

  const handleTitleChange = useCallback(
    (value: string) => {
      setTitle(value)
      markEdited()
    },
    [markEdited],
  )

  const handleEvalChange = useCallback(
    (key: string, value: string) => {
      setEvaluations((prev) => ({ ...prev, [key]: value }))
      markEdited()
    },
    [markEdited],
  )

  const handleAddTag = useCallback(() => {
    const tag = tagInput.trim()
    if (!tag || tags.includes(tag)) return
    setTags((prev) => [...prev, tag])
    setTagInput('')
    markEdited()
  }, [tagInput, tags, markEdited])

  const handleRemoveTag = useCallback(
    (tag: string) => {
      setTags((prev) => prev.filter((t) => t !== tag))
      markEdited()
    },
    [markEdited],
  )

  const toggleSection = useCallback((key: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }, [])

  const handleSave = useCallback(async () => {
    if (!uuid) return
    setSaving(true)
    try {
      await stockApi.updateEvaluation(uuid, { title, evaluations, tags })
      setEdited(false)
    } catch (err) {
      console.error('Save failed:', err)
    } finally {
      setSaving(false)
    }
  }, [uuid, title, evaluations, tags])

  const handleDelete = useCallback(async () => {
    if (!uuid) return
    if (!window.confirm(t('stockHub.confirmDelete', '确定要删除这条评估记录吗？'))) return
    setDeleting(true)
    try {
      await stockApi.deleteEvaluation(uuid)
      navigate('/stock-hub/evaluations')
    } catch (err) {
      console.error('Delete failed:', err)
      setDeleting(false)
    }
  }, [uuid, navigate, t])

  // Loading state
  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  // Error state
  if (error || !data) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => navigate('/stock-hub/evaluations')}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('stockHub.backToList', '返回列表')}
        </button>
        <div className="flex h-48 items-center justify-center text-destructive">
          {error || 'Evaluation not found'}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <button
        onClick={() => navigate('/stock-hub/evaluations')}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        {t('stockHub.backToList', '返回列表')}
      </button>

      {/* Title */}
      <div className="flex items-center gap-3">
        {editingTitle ? (
          <input
            value={title}
            onChange={(e) => handleTitleChange(e.target.value)}
            onBlur={() => setEditingTitle(false)}
            onKeyDown={(e) => e.key === 'Enter' && setEditingTitle(false)}
            autoFocus
            className="flex-1 rounded-md border bg-background px-3 py-1.5 text-2xl font-bold focus:outline-none focus:ring-1 focus:ring-primary"
          />
        ) : (
          <h1
            className="flex-1 cursor-pointer text-2xl font-bold hover:text-primary"
            onClick={() => setEditingTitle(true)}
            title={t('stockHub.clickToEdit', '点击编辑')}
          >
            {title}
            <Edit3 className="ml-2 inline h-4 w-4 text-muted-foreground" />
          </h1>
        )}
      </div>

      {/* Meta info */}
      <div className="rounded-lg border p-4 space-y-3">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">{t('stockHub.factorName', '因子名称')}:</span>{' '}
            <span className="font-medium">{data.factor_name}</span>
          </div>
          <div>
            <span className="text-muted-foreground">{t('stockHub.createdAt', '创建时间')}:</span>{' '}
            <span className="font-medium">{new Date(data.created_at).toLocaleString()}</span>
          </div>
          <div>
            <span className="text-muted-foreground">{t('stockHub.updatedAt', '更新时间')}:</span>{' '}
            <span className="font-medium">{new Date(data.updated_at).toLocaleString()}</span>
          </div>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap items-center gap-2">
          <Tag className="h-4 w-4 text-muted-foreground" />
          {tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium"
            >
              {tag}
              <button
                onClick={() => handleRemoveTag(tag)}
                className="ml-0.5 text-muted-foreground hover:text-destructive"
              >
                &times;
              </button>
            </span>
          ))}
          <div className="inline-flex items-center gap-1">
            <input
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddTag()}
              placeholder={t('stockHub.addTag', '添加标签...')}
              className="w-24 rounded-md border bg-background px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <button
              onClick={handleAddTag}
              disabled={!tagInput.trim()}
              className="rounded-md bg-muted px-2 py-0.5 text-xs hover:bg-muted/80 disabled:opacity-50"
            >
              +
            </button>
          </div>
        </div>
      </div>

      {/* Evaluation sections */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">{t('stockHub.evaluationContent', '评估内容')}</h2>
        {Object.entries(evaluations).map(([key, text]) => {
          const isExpanded = expandedSections.has(key)
          const label = EVAL_TYPE_LABELS[key] || key

          return (
            <div key={key} className="rounded-md border">
              <button
                onClick={() => toggleSection(key)}
                className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium hover:bg-muted/50"
              >
                <span>{label}</span>
                <span className="text-xs text-muted-foreground">
                  {text.length} {t('stockHub.chars', '字')}
                </span>
              </button>
              {isExpanded && (
                <div className="border-t px-3 py-2">
                  <textarea
                    value={text}
                    onChange={(e) => handleEvalChange(key, e.target.value)}
                    className="w-full min-h-[150px] rounded-md border bg-background p-2 text-sm leading-relaxed resize-y focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              )}
            </div>
          )
        })}

        {Object.keys(evaluations).length === 0 && (
          <p className="text-sm text-muted-foreground">{t('stockHub.noEvaluations', '暂无评估内容')}</p>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={!edited || saving}
          className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {t('stockHub.saveChanges', '保存修改')}
        </button>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="flex items-center gap-2 rounded-md bg-destructive px-4 py-2 text-sm text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50"
        >
          {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          {t('stockHub.delete', '删除')}
        </button>
      </div>
    </div>
  )
}
