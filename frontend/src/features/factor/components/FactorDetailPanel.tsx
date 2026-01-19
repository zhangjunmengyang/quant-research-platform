/**
 * Factor Detail Side Panel Component
 * Editable panel for viewing and editing factor metadata
 */

import { useEffect, useState, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useMutation } from '@tanstack/react-query'
import { useFactorStore, useFactorMutations } from '../'
import { factorApi } from '../api'
import { pipelineApi, type FillableField } from '../pipeline-api'
import type { Factor, FactorUpdate } from '../types'
import { cn, stripPyExtension } from '@/lib/utils'
import { Loader2, X, Copy, Check, Edit2, Save, Sparkles, Ban, Undo2, Trash2 } from 'lucide-react'
import { toast } from '@/components/ui/toast'

// 可自动生成的字段
const AUTO_FILL_FIELDS: { value: FillableField; label: string }[] = [
  { value: 'style', label: '风格' },
  { value: 'tags', label: '标签' },
  { value: 'formula', label: '公式' },
  { value: 'input_data', label: '输入数据' },
  { value: 'value_range', label: '值域' },
  { value: 'description', label: '刻画特征' },
  { value: 'analysis', label: '深度分析' },
  { value: 'llm_score', label: 'LLM评分' },
]

interface FactorDetailPanelProps {
  factor: Factor
  onClose: () => void
}

export function FactorDetailPanel({ factor, onClose }: FactorDetailPanelProps) {
  const { verifyFactor, unverifyFactor, updateFactor, excludeFactor, unexcludeFactor, deleteFactor } = useFactorMutations()
  const [fullFactor, setFullFactor] = useState<Factor | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  // 自动生成相关状态
  const [showAutoFill, setShowAutoFill] = useState(false)
  const [selectedAutoFields, setSelectedAutoFields] = useState<FillableField[]>([])

  // Form state for editing
  const [formData, setFormData] = useState<FactorUpdate>({})

  // Load full factor details including code_content
  useEffect(() => {
    const loadFactor = async () => {
      setLoading(true)
      try {
        const data = await factorApi.get(factor.filename)
        setFullFactor(data)
        // Initialize form data
        setFormData({
          style: data.style || '',
          tags: data.tags || '',
          formula: data.formula || '',
          input_data: data.input_data || '',
          value_range: data.value_range || '',
          description: data.description || '',
          analysis: data.analysis || '',
          llm_score: data.llm_score,
        })
      } catch (error) {
        console.error('Failed to load factor:', error)
        setFullFactor(factor)
        setFormData({
          style: factor.style || '',
          tags: factor.tags || '',
          formula: factor.formula || '',
          input_data: factor.input_data || '',
          value_range: factor.value_range || '',
          description: factor.description || '',
          analysis: factor.analysis || '',
          llm_score: factor.llm_score,
        })
      } finally {
        setLoading(false)
      }
    }
    loadFactor()
  }, [factor.filename])

  const displayFactor = fullFactor || factor

  const handleVerify = () => {
    const factorName = stripPyExtension(displayFactor.filename)
    if (displayFactor.verified) {
      unverifyFactor.mutate(displayFactor.filename, {
        onSuccess: (data) => {
          setFullFactor(data)
          toast.success('已取消校验', `${factorName} 已标记为未校验`)
        },
        onError: (error) => {
          toast.error('取消校验失败', (error as Error).message)
        },
      })
    } else {
      verifyFactor.mutate({ filename: displayFactor.filename }, {
        onSuccess: (data) => {
          setFullFactor(data)
          toast.success('已标记校验', `${factorName} 已标记为已校验`)
        },
        onError: (error) => {
          toast.error('标记校验失败', (error as Error).message)
        },
      })
    }
  }

  const handleExclude = () => {
    const factorName = stripPyExtension(displayFactor.filename)
    if (displayFactor.excluded) {
      unexcludeFactor.mutate(displayFactor.filename, {
        onSuccess: (data) => {
          setFullFactor(data)
          toast.success('已取消排除', `${factorName} 已恢复`)
        },
        onError: (error) => {
          toast.error('取消排除失败', (error as Error).message)
        },
      })
    } else {
      excludeFactor.mutate({ filename: displayFactor.filename }, {
        onSuccess: (data) => {
          setFullFactor(data)
          toast.info('已排除', `${factorName} 已标记为排除`)
        },
        onError: (error) => {
          toast.error('排除失败', (error as Error).message)
        },
      })
    }
  }

  const handleDelete = () => {
    const factorName = stripPyExtension(displayFactor.filename)
    deleteFactor.mutate(displayFactor.filename, {
      onSuccess: () => {
        toast.success('已删除', `${factorName} 已从因子库中删除`)
        onClose()
      },
      onError: (error) => {
        toast.error('删除失败', (error as Error).message)
      },
    })
    setShowDeleteConfirm(false)
  }

  const handleCopyCode = async () => {
    const code = displayFactor.code_content || ''
    if (code) {
      try {
        await navigator.clipboard.writeText(code)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      } catch (err) {
        console.error('Failed to copy:', err)
      }
    }
  }

  const handleStartEdit = () => {
    setIsEditing(true)
  }

  const handleCancelEdit = () => {
    // Reset form data to current factor values
    setFormData({
      style: displayFactor.style || '',
      tags: displayFactor.tags || '',
      formula: displayFactor.formula || '',
      input_data: displayFactor.input_data || '',
      value_range: displayFactor.value_range || '',
      description: displayFactor.description || '',
      analysis: displayFactor.analysis || '',
      llm_score: displayFactor.llm_score,
    })
    setIsEditing(false)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      // 使用 mutation 更新，它会自动 invalidate queries
      updateFactor.mutate(
        { filename: displayFactor.filename, update: formData },
        {
          onSuccess: (data) => {
            setFullFactor(data)
            setIsEditing(false)
          },
          onError: (error) => {
            console.error('Failed to save factor:', error)
          },
          onSettled: () => {
            setSaving(false)
          }
        }
      )
    } catch (error) {
      console.error('Failed to save factor:', error)
      setSaving(false)
    }
  }

  const handleFormChange = (field: keyof FactorUpdate, value: string | number | undefined) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  // Check if form has changes
  const hasChanges = useMemo(() => {
    return (
      formData.style !== (displayFactor.style || '') ||
      formData.tags !== (displayFactor.tags || '') ||
      formData.formula !== (displayFactor.formula || '') ||
      formData.input_data !== (displayFactor.input_data || '') ||
      formData.value_range !== (displayFactor.value_range || '') ||
      formData.description !== (displayFactor.description || '') ||
      formData.analysis !== (displayFactor.analysis || '') ||
      formData.llm_score !== displayFactor.llm_score
    )
  }, [formData, displayFactor])

  // 自动填充 mutation（预览模式，不直接保存到数据库）
  const autoFillMutation = useMutation({
    mutationFn: (fields: FillableField[]) => {
      if (!displayFactor?.filename) {
        throw new Error('因子信息不完整')
      }
      return pipelineApi.fill({
        factors: [displayFactor.filename],
        fields,
        mode: 'full',
        preview: true, // 预览模式：生成但不保存
      })
    },
    onSuccess: (result) => {
      // 从 generated 中提取生成的值，填入表单
      const generated = result.generated?.[displayFactor.filename]
      if (generated) {
        setFormData((prev) => ({
          ...prev,
          ...(generated.style !== undefined && { style: generated.style }),
          ...(generated.tags !== undefined && { tags: generated.tags }),
          ...(generated.formula !== undefined && { formula: generated.formula }),
          ...(generated.input_data !== undefined && { input_data: generated.input_data }),
          ...(generated.value_range !== undefined && { value_range: generated.value_range }),
          ...(generated.description !== undefined && { description: generated.description }),
          ...(generated.analysis !== undefined && { analysis: generated.analysis }),
          ...(generated.llm_score !== undefined && { llm_score: parseFloat(generated.llm_score) }),
        }))
      }
      setShowAutoFill(false)
      setSelectedAutoFields([])
      // 注意：不刷新列表，因为数据还没保存
    },
  })

  const handleToggleAutoField = (field: FillableField) => {
    setSelectedAutoFields((prev) =>
      prev.includes(field) ? prev.filter((f) => f !== field) : [...prev, field]
    )
  }

  const handleAutoFill = () => {
    if (selectedAutoFields.length === 0) return
    autoFillMutation.mutate(selectedAutoFields)
  }

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-[50vw] min-w-[600px] max-w-[900px] border-l bg-background shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-6 py-4">
        <h2 className="text-lg font-semibold">{stripPyExtension(displayFactor.filename)}</h2>
        <div className="flex items-center gap-2">
          {!loading && (
            isEditing ? (
              <>
                <button
                  onClick={handleCancelEdit}
                  disabled={saving || autoFillMutation.isPending}
                  className="rounded-md border border-input bg-background px-4 py-1.5 text-sm font-medium hover:bg-accent"
                >
                  取消
                </button>
                <button
                  onClick={() => setShowAutoFill(!showAutoFill)}
                  disabled={saving || autoFillMutation.isPending}
                  className={cn(
                    'flex items-center gap-1.5 rounded-md border px-4 py-1.5 text-sm font-medium transition-colors',
                    showAutoFill
                      ? 'border-purple-500 bg-purple-50 text-purple-700'
                      : 'border-input bg-background hover:bg-accent'
                  )}
                >
                  <Sparkles className="h-4 w-4" />
                  自动生成
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving || !hasChanges || autoFillMutation.isPending}
                  className={cn(
                    'rounded-md px-4 py-1.5 text-sm font-medium transition-colors flex items-center gap-1.5',
                    hasChanges
                      ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                      : 'bg-muted text-muted-foreground cursor-not-allowed'
                  )}
                >
                  {saving ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      保存中
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      保存
                    </>
                  )}
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={handleStartEdit}
                  className="flex items-center gap-1.5 rounded-md border border-input bg-background px-4 py-1.5 text-sm font-medium hover:bg-accent"
                >
                  <Edit2 className="h-4 w-4" />
                  编辑
                </button>
                <button
                  onClick={handleVerify}
                  disabled={verifyFactor.isPending || unverifyFactor.isPending}
                  className={cn(
                    'rounded-md px-4 py-1.5 text-sm font-medium transition-colors',
                    displayFactor.verified
                      ? 'bg-red-600 text-white hover:bg-red-700'
                      : 'bg-blue-600 text-white hover:bg-blue-700',
                    (verifyFactor.isPending || unverifyFactor.isPending) && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  {(verifyFactor.isPending || unverifyFactor.isPending) ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : displayFactor.verified ? (
                    '取消校验'
                  ) : (
                    '标记校验'
                  )}
                </button>
                <button
                  onClick={handleExclude}
                  disabled={excludeFactor.isPending || unexcludeFactor.isPending}
                  className={cn(
                    'flex items-center gap-1.5 rounded-md px-4 py-1.5 text-sm font-medium transition-colors',
                    displayFactor.excluded
                      ? 'bg-green-600 text-white hover:bg-green-700'
                      : 'bg-red-600 text-white hover:bg-red-700',
                    (excludeFactor.isPending || unexcludeFactor.isPending) && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  {(excludeFactor.isPending || unexcludeFactor.isPending) ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : displayFactor.excluded ? (
                    <>
                      <Undo2 className="h-4 w-4" />
                      取消排除
                    </>
                  ) : (
                    <>
                      <Ban className="h-4 w-4" />
                      排除
                    </>
                  )}
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  disabled={deleteFactor.isPending}
                  className={cn(
                    'flex items-center gap-1.5 rounded-md border border-red-300 px-4 py-1.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-50',
                    deleteFactor.isPending && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  {deleteFactor.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <Trash2 className="h-4 w-4" />
                      删除
                    </>
                  )}
                </button>
              </>
            )
          )}
          <button
            onClick={onClose}
            className="rounded-md p-2 hover:bg-accent"
            aria-label="关闭"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
          <div className="w-[480px] rounded-lg bg-background p-6 shadow-xl">
            <h3 className="text-lg font-semibold">确认删除</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              确定要删除因子 <span className="font-medium text-foreground">{stripPyExtension(displayFactor.filename)}</span> 吗?
            </p>
            <p className="mt-1 text-sm text-red-600">
              此操作将同时删除因子的数据库记录和代码文件，不可恢复。
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent"
              >
                取消
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteFactor.isPending}
                className="flex items-center gap-1.5 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteFactor.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    删除中...
                  </>
                ) : (
                  '确认删除'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Auto Fill Panel */}
      {showAutoFill && isEditing && (
        <div className="border-b bg-purple-50/50 px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <p className="text-sm font-medium text-purple-900 mb-2">选择要自动生成的字段</p>
              <div className="flex flex-wrap gap-2">
                {AUTO_FILL_FIELDS.map(({ value, label }) => (
                  <button
                    key={value}
                    onClick={() => handleToggleAutoField(value)}
                    disabled={autoFillMutation.isPending}
                    className={cn(
                      'rounded-full px-3 py-1 text-xs font-medium transition-colors',
                      selectedAutoFields.includes(value)
                        ? 'bg-purple-600 text-white'
                        : 'bg-white text-purple-700 border border-purple-300 hover:bg-purple-100'
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <button
              onClick={handleAutoFill}
              disabled={selectedAutoFields.length === 0 || autoFillMutation.isPending}
              className="flex items-center gap-1.5 rounded-md bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
            >
              {autoFillMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  生成中...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  开始生成
                </>
              )}
            </button>
          </div>
          {autoFillMutation.isError && (
            <p className="mt-2 text-xs text-red-600">
              生成失败: {(autoFillMutation.error as Error)?.message}
            </p>
          )}
        </div>
      )}

      {/* Content */}
      <div className={cn(
        "overflow-y-auto p-6",
        showAutoFill && isEditing ? "h-[calc(100vh-136px)]" : "h-[calc(100vh-65px)]"
      )}>
        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* Status Badges */}
            <div className="mb-6 flex flex-wrap gap-2">
              {displayFactor.excluded && (
                <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-800">
                  已排除
                </span>
              )}
              <span
                className={cn(
                  'rounded-full px-3 py-1 text-xs font-medium',
                  displayFactor.verified
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-800'
                )}
              >
                {displayFactor.verified ? '已校验' : '未审查'}
              </span>
              {/* Style Tags Display */}
              {(isEditing ? formData.style : displayFactor.style)?.split(',').filter(s => s.trim()).map((style, idx) => (
                <span key={`style-${idx}`} className="rounded-full bg-purple-100 px-3 py-1 text-xs font-medium text-purple-800">
                  {style.trim()}
                </span>
              ))}
              {/* Tags Display */}
              {(isEditing ? formData.tags : displayFactor.tags)?.split(',').filter(t => t.trim()).map((tag, idx) => (
                <span key={`tag-${idx}`} className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800">
                  {tag.trim()}
                </span>
              ))}
            </div>

            {/* Info Sections */}
            <div className="space-y-6">
              {/* Basic Info */}
              <section>
                <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
                  基本信息
                </h3>
                {isEditing ? (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="mb-1.5 block text-sm text-muted-foreground">
                        风格 <code className="text-xs bg-muted px-1 rounded">style</code>
                        <span className="ml-2 text-xs text-gray-400">英文逗号分隔，3个标签</span>
                      </label>
                      <input
                        type="text"
                        value={formData.style || ''}
                        onChange={(e) => handleFormChange('style', e.target.value)}
                        placeholder="波动率, 反转, 情绪..."
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-sm text-muted-foreground">
                        评分 <code className="text-xs bg-muted px-1 rounded">llm_score</code>
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="5"
                        value={formData.llm_score ?? ''}
                        onChange={(e) => {
                          const val = e.target.value
                          handleFormChange('llm_score', val === '' ? undefined : parseFloat(val))
                        }}
                        placeholder="0-5"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-sm text-muted-foreground">
                        输入数据 <code className="text-xs bg-muted px-1 rounded">input_data</code>
                      </label>
                      <input
                        type="text"
                        value={formData.input_data || ''}
                        onChange={(e) => handleFormChange('input_data', e.target.value)}
                        placeholder="close, volume..."
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-sm text-muted-foreground">
                        值域 <code className="text-xs bg-muted px-1 rounded">value_range</code>
                      </label>
                      <input
                        type="text"
                        value={formData.value_range || ''}
                        onChange={(e) => handleFormChange('value_range', e.target.value)}
                        placeholder="[-1, 1]..."
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      />
                    </div>
                    <div className="col-span-2">
                      <label className="mb-1.5 block text-sm text-muted-foreground">
                        标签 <code className="text-xs bg-muted px-1 rounded">tags</code>
                        <span className="ml-2 text-xs text-gray-400">英文逗号分隔</span>
                      </label>
                      <input
                        type="text"
                        value={formData.tags || ''}
                        onChange={(e) => handleFormChange('tags', e.target.value)}
                        placeholder="滚动窗口, 量价结合, 趋势跟随..."
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      />
                    </div>
                  </div>
                ) : (
                  <dl className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <dt className="text-muted-foreground">风格 <code className="text-xs bg-muted px-1 rounded">style</code></dt>
                      <dd className="font-medium">{displayFactor.style || '-'}</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">评分 <code className="text-xs bg-muted px-1 rounded">llm_score</code></dt>
                      <dd className="font-medium">{displayFactor.llm_score ?? '-'}</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">输入数据 <code className="text-xs bg-muted px-1 rounded">input_data</code></dt>
                      <dd className="font-medium">{displayFactor.input_data || '-'}</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">值域 <code className="text-xs bg-muted px-1 rounded">value_range</code></dt>
                      <dd className="font-medium">{displayFactor.value_range || '-'}</dd>
                    </div>
                    <div className="col-span-2">
                      <dt className="text-muted-foreground">标签 <code className="text-xs bg-muted px-1 rounded">tags</code></dt>
                      <dd className="font-medium">{displayFactor.tags || '-'}</dd>
                    </div>
                  </dl>
                )}
              </section>

              {/* Formula */}
              <section>
                <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
                  计算公式 <code className="text-xs bg-muted px-1 rounded font-normal">formula</code>
                </h3>
                {isEditing ? (
                  <textarea
                    value={formData.formula || ''}
                    onChange={(e) => handleFormChange('formula', e.target.value)}
                    placeholder="输入计算公式..."
                    rows={3}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
                  />
                ) : (
                  <div className="rounded-md bg-muted p-3 font-mono text-sm">
                    {displayFactor.formula || '-'}
                  </div>
                )}
              </section>

              {/* Description (刻画特征) */}
              <section>
                <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
                  刻画特征 <code className="text-xs bg-muted px-1 rounded font-normal">description</code>
                </h3>
                {isEditing ? (
                  <textarea
                    value={formData.description || ''}
                    onChange={(e) => handleFormChange('description', e.target.value)}
                    placeholder="描述因子刻画的市场特征..."
                    rows={4}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                ) : (
                  <p className="text-sm leading-relaxed">{displayFactor.description || '-'}</p>
                )}
              </section>

              {/* Analysis (深度分析) */}
              <section>
                <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
                  深度分析 <code className="text-xs bg-muted px-1 rounded font-normal">analysis</code>
                </h3>
                {isEditing ? (
                  <textarea
                    value={formData.analysis || ''}
                    onChange={(e) => handleFormChange('analysis', e.target.value)}
                    placeholder="输入深度分析内容..."
                    rows={8}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                ) : displayFactor.analysis ? (
                  <div className="prose prose-sm max-w-none">
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">
                      {displayFactor.analysis}
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">-</p>
                )}
              </section>

              {/* Code - Full Source */}
              {displayFactor.code_content && (
                <section>
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-muted-foreground">
                      因子代码
                    </h3>
                    <button
                      onClick={handleCopyCode}
                      className="flex items-center gap-1 rounded px-2 py-1 text-xs hover:bg-accent"
                    >
                      {copied ? (
                        <>
                          <Check className="h-3 w-3 text-green-600" />
                          已复制
                        </>
                      ) : (
                        <>
                          <Copy className="h-3 w-3" />
                          复制
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="max-h-[500px] overflow-auto rounded-md bg-slate-900 p-4 text-xs text-slate-100">
                    <code>{displayFactor.code_content}</code>
                  </pre>
                </section>
              )}

              {/* Code Path (fallback) */}
              {displayFactor.code_path && !displayFactor.code_content && (
                <section>
                  <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
                    代码路径
                  </h3>
                  <p className="rounded-md bg-muted p-3 font-mono text-sm">
                    {displayFactor.code_path}
                  </p>
                </section>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

/**
 * Panel Wrapper with Backdrop
 * 使用 Portal 渲染到 body，确保遮罩层完全覆盖
 */
export function FactorDetailPanelWrapper() {
  const { selectedFactor, detailPanelOpen, closeDetailPanel } = useFactorStore()

  if (!detailPanelOpen || !selectedFactor) {
    return null
  }

  return createPortal(
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/50"
        style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0 }}
        onClick={closeDetailPanel}
      />
      {/* Panel */}
      <FactorDetailPanel factor={selectedFactor} onClose={closeDetailPanel} />
    </>,
    document.body
  )
}
