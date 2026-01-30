/**
 * Factor Detail Page
 * 因子详情页 - 独立页面形式展示因子完整信息
 */

import { useEffect, useState, useMemo, useCallback } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { factorApi } from '@/features/factor/api'
import { pipelineApi, type FillableField } from '@/features/factor/pipeline-api'
import { useFactorMutations } from '@/features/factor'
import type { Factor, FactorUpdate, ParamAnalysisData, StrategyConfig } from '@/features/factor/types'
import { isParamAnalysis2D } from '@/features/factor/types'
import { cn, stripPyExtension } from '@/lib/utils'
import {
  Loader2,
  ArrowLeft,
  Copy,
  Check,
  Edit2,
  Save,
  Sparkles,
  Ban,
  Undo2,
  Trash2,
  BarChart3,
} from 'lucide-react'
import { toast } from '@/components/ui/toast'
import { BaseChart } from '@/components/charts'
import { EntityGraph } from '@/features/graph'

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

// 验证状态常量
const VERIFICATION_STATUS = {
  UNVERIFIED: 0,
  PASSED: 1,
  FAILED: 2,
}

export function Component() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const { verifyFactor, unverifyFactor, updateFactor, excludeFactor, unexcludeFactor, deleteFactor } = useFactorMutations()

  const [factor, setFactor] = useState<Factor | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  // 自动生成相关状态
  const [showAutoFill, setShowAutoFill] = useState(false)
  const [selectedAutoFields, setSelectedAutoFields] = useState<FillableField[]>([])

  // Form state for editing
  const [formData, setFormData] = useState<FactorUpdate>({})

  // 文件名处理：直接使用 URL 参数，后端会统一处理 .py 后缀
  const filename = id || ''

  // 安全的后退函数
  const handleBack = useCallback(() => {
    if (location.key === 'default') {
      navigate('/factors', { replace: true })
    } else {
      navigate(-1)
    }
  }, [navigate, location.key])

  // Load factor details
  useEffect(() => {
    if (!filename) return

    const loadFactor = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await factorApi.get(filename)
        setFactor(data)
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
      } catch (err) {
        console.error('Failed to load factor:', err)
        setError((err as Error).message || '加载因子失败')
      } finally {
        setLoading(false)
      }
    }
    loadFactor()
  }, [filename])

  const handleVerify = () => {
    if (!factor) return
    const factorName = stripPyExtension(factor.filename)
    if (factor.verification_status === VERIFICATION_STATUS.PASSED) {
      unverifyFactor.mutate(factor.filename, {
        onSuccess: (data) => {
          setFactor(data)
          toast.success('已重置验证', `${factorName} 已重置为未验证`)
        },
        onError: (error) => {
          toast.error('重置验证失败', (error as Error).message)
        },
      })
    } else {
      verifyFactor.mutate({ filename: factor.filename }, {
        onSuccess: (data) => {
          setFactor(data)
          toast.success('已标记通过', `${factorName} 已标记为验证通过`)
        },
        onError: (error) => {
          toast.error('标记通过失败', (error as Error).message)
        },
      })
    }
  }

  const handleExclude = () => {
    if (!factor) return
    const factorName = stripPyExtension(factor.filename)
    if (factor.excluded) {
      unexcludeFactor.mutate(factor.filename, {
        onSuccess: (data) => {
          setFactor(data)
          toast.success('已取消排除', `${factorName} 已恢复`)
        },
        onError: (error) => {
          toast.error('取消排除失败', (error as Error).message)
        },
      })
    } else {
      excludeFactor.mutate({ filename: factor.filename }, {
        onSuccess: (data) => {
          setFactor(data)
          toast.info('已排除', `${factorName} 已标记为排除`)
        },
        onError: (error) => {
          toast.error('排除失败', (error as Error).message)
        },
      })
    }
  }

  const handleDelete = () => {
    if (!factor) return
    const factorName = stripPyExtension(factor.filename)
    deleteFactor.mutate(factor.filename, {
      onSuccess: () => {
        toast.success('已删除', `${factorName} 已从因子库中删除`)
        navigate('/factors', { replace: true })
      },
      onError: (error) => {
        toast.error('删除失败', (error as Error).message)
      },
    })
    setShowDeleteConfirm(false)
  }

  const handleCopyCode = async () => {
    const code = factor?.code_content || ''
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
    if (!factor) return
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
    setIsEditing(false)
  }

  const handleSave = () => {
    if (!factor) return
    setSaving(true)
    updateFactor.mutate(
      { filename: factor.filename, update: formData },
      {
        onSuccess: (data) => {
          setFactor(data)
          setIsEditing(false)
        },
        onError: (error) => {
          console.error('Failed to save factor:', error)
        },
        onSettled: () => {
          setSaving(false)
        },
      }
    )
  }

  const handleFormChange = (field: keyof FactorUpdate, value: string | number | undefined) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  // Check if form has changes
  const hasChanges = useMemo(() => {
    if (!factor) return false
    return (
      formData.style !== (factor.style || '') ||
      formData.tags !== (factor.tags || '') ||
      formData.formula !== (factor.formula || '') ||
      formData.input_data !== (factor.input_data || '') ||
      formData.value_range !== (factor.value_range || '') ||
      formData.description !== (factor.description || '') ||
      formData.analysis !== (factor.analysis || '') ||
      formData.llm_score !== factor.llm_score
    )
  }, [formData, factor])

  // 自动填充 mutation
  const autoFillMutation = useMutation({
    mutationFn: (fields: FillableField[]) => {
      if (!factor?.filename) {
        throw new Error('因子信息不完整')
      }
      return pipelineApi.fill({
        factors: [factor.filename],
        fields,
        mode: 'full',
        preview: true,
      })
    },
    onSuccess: (result) => {
      if (!factor) return
      const generated = result.generated?.[factor.filename]
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

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error || !factor) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <p className="text-destructive">
          {error || '因子不存在'}
        </p>
        <button
          type="button"
          onClick={handleBack}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          返回
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            type="button"
            onClick={handleBack}
            className="mb-2 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            返回
          </button>
          <h1 className="text-2xl font-bold">{stripPyExtension(factor.filename)}</h1>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {isEditing ? (
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
                  factor.verification_status === VERIFICATION_STATUS.PASSED
                    ? 'bg-orange-600 text-white hover:bg-orange-700'
                    : 'bg-green-600 text-white hover:bg-green-700',
                  (verifyFactor.isPending || unverifyFactor.isPending) && 'opacity-50 cursor-not-allowed'
                )}
              >
                {(verifyFactor.isPending || unverifyFactor.isPending) ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : factor.verification_status === VERIFICATION_STATUS.PASSED ? (
                  '重置验证'
                ) : (
                  '标记通过'
                )}
              </button>
              <button
                onClick={handleExclude}
                disabled={excludeFactor.isPending || unexcludeFactor.isPending}
                className={cn(
                  'flex items-center gap-1.5 rounded-md px-4 py-1.5 text-sm font-medium transition-colors',
                  factor.excluded
                    ? 'bg-green-600 text-white hover:bg-green-700'
                    : 'bg-red-600 text-white hover:bg-red-700',
                  (excludeFactor.isPending || unexcludeFactor.isPending) && 'opacity-50 cursor-not-allowed'
                )}
              >
                {(excludeFactor.isPending || unexcludeFactor.isPending) ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : factor.excluded ? (
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
          )}
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
          <div className="w-[480px] rounded-lg bg-background p-6 shadow-xl">
            <h3 className="text-lg font-semibold">确认删除</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              确定要删除因子 <span className="font-medium text-foreground">{stripPyExtension(factor.filename)}</span> 吗?
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
        <div className="rounded-lg border bg-purple-50/50 p-4">
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

      {/* Status Badges */}
      <div className="flex flex-wrap gap-2">
        {factor.excluded && (
          <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-800">
            已排除
          </span>
        )}
        <span
          className={cn(
            'rounded-full px-3 py-1 text-xs font-medium',
            factor.verification_status === VERIFICATION_STATUS.PASSED
              ? 'bg-green-100 text-green-800'
              : factor.verification_status === VERIFICATION_STATUS.FAILED
              ? 'bg-red-100 text-red-800'
              : 'bg-gray-100 text-gray-800'
          )}
        >
          {factor.verification_status === VERIFICATION_STATUS.PASSED
            ? '通过'
            : factor.verification_status === VERIFICATION_STATUS.FAILED
            ? '废弃'
            : '未验证'}
        </span>
        {(isEditing ? formData.style : factor.style)?.split(',').filter(s => s.trim()).map((style, idx) => (
          <span key={`style-${idx}`} className="rounded-full bg-purple-100 px-3 py-1 text-xs font-medium text-purple-800">
            {style.trim()}
          </span>
        ))}
        {(isEditing ? formData.tags : factor.tags)?.split(',').filter(t => t.trim()).map((tag, idx) => (
          <span key={`tag-${idx}`} className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800">
            {tag.trim()}
          </span>
        ))}
      </div>

      {/* Basic Info */}
      <div className="rounded-lg border bg-card p-4">
        <h3 className="mb-3 text-sm font-semibold text-muted-foreground">基本信息</h3>
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
              <dt className="text-muted-foreground">风格</dt>
              <dd className="font-medium">{factor.style || '-'}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">评分</dt>
              <dd className="font-medium">{factor.llm_score ?? '-'}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">输入数据</dt>
              <dd className="font-medium">{factor.input_data || '-'}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">值域</dt>
              <dd className="font-medium">{factor.value_range || '-'}</dd>
            </div>
            <div className="col-span-2">
              <dt className="text-muted-foreground">标签</dt>
              <dd className="font-medium">{factor.tags || '-'}</dd>
            </div>
          </dl>
        )}
      </div>

      {/* Formula */}
      <div className="rounded-lg border bg-card p-4">
        <h3 className="mb-3 text-sm font-semibold text-muted-foreground">计算公式</h3>
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
            {factor.formula || '-'}
          </div>
        )}
      </div>

      {/* Description */}
      <div className="rounded-lg border bg-card p-4">
        <h3 className="mb-3 text-sm font-semibold text-muted-foreground">刻画特征</h3>
        {isEditing ? (
          <textarea
            value={formData.description || ''}
            onChange={(e) => handleFormChange('description', e.target.value)}
            placeholder="描述因子刻画的市场特征..."
            rows={4}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        ) : (
          <p className="text-sm leading-relaxed">{factor.description || '-'}</p>
        )}
      </div>

      {/* Analysis */}
      <div className="rounded-lg border bg-card p-4">
        <h3 className="mb-3 text-sm font-semibold text-muted-foreground">深度分析</h3>
        {isEditing ? (
          <textarea
            value={formData.analysis || ''}
            onChange={(e) => handleFormChange('analysis', e.target.value)}
            placeholder="输入深度分析内容..."
            rows={8}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        ) : factor.analysis ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{factor.analysis}</p>
        ) : (
          <p className="text-sm text-muted-foreground">-</p>
        )}
      </div>

      {/* Parameter Analysis */}
      {factor.param_analysis && (
        <ParamAnalysisSection paramAnalysisJson={factor.param_analysis} />
      )}

      {/* Knowledge Graph */}
      <EntityGraph
        entityType="factor"
        entityId={factor.filename}
        entityName={stripPyExtension(factor.filename)}
        height={300}
      />

      {/* Code */}
      {factor.code_content && (
        <div className="rounded-lg border bg-card p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-muted-foreground">因子代码</h3>
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
            <code>{factor.code_content}</code>
          </pre>
        </div>
      )}

      {/* Metadata */}
      <div className="text-xs text-muted-foreground">
        <p>文件名: {factor.filename}</p>
        <p>代码路径: {factor.code_path || '-'}</p>
      </div>
    </div>
  )
}

/** 带配置名的参数分析数据 */
interface ParamAnalysisDataWithConfig extends ParamAnalysisData {
  config_name?: string
  description?: string
}

/**
 * Parameter Analysis Section
 * 支持单个对象或数组格式的 param_analysis
 */
function ParamAnalysisSection({ paramAnalysisJson }: { paramAnalysisJson: string }) {
  const paramAnalysisList = useMemo<ParamAnalysisDataWithConfig[]>(() => {
    try {
      const parsed = JSON.parse(paramAnalysisJson)
      // 兼容数组格式和单个对象格式
      if (Array.isArray(parsed)) {
        return parsed
      }
      return [parsed]
    } catch {
      return []
    }
  }, [paramAnalysisJson])

  if (paramAnalysisList.length === 0) {
    return null
  }

  return (
    <div className="space-y-4">
      {paramAnalysisList.map((paramAnalysis, index) => (
        <ParamAnalysisCard
          key={paramAnalysis.config_name || index}
          paramAnalysis={paramAnalysis}
          showConfigName={paramAnalysisList.length > 1}
        />
      ))}
    </div>
  )
}

/**
 * Single Parameter Analysis Card
 */
function ParamAnalysisCard({
  paramAnalysis,
  showConfigName,
}: {
  paramAnalysis: ParamAnalysisDataWithConfig
  showConfigName: boolean
}) {
  const [showAllResults, setShowAllResults] = useState(false)

  const { config, grid_keys, best_result, results, indicator, chart, updated_at, config_name, description } = paramAnalysis
  const is2D = isParamAnalysis2D(paramAnalysis)

  if (!config || !grid_keys || !best_result) {
    return (
      <div className="rounded-lg border bg-card p-4">
        <div className="mb-3 flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold text-muted-foreground">参数敏感性分析</h3>
          {showConfigName && config_name && (
            <span className="text-sm font-medium text-foreground">{config_name}</span>
          )}
        </div>
        <p className="text-sm text-muted-foreground">数据格式不兼容，请重新运行参数分析</p>
      </div>
    )
  }

  const firstStrategy: StrategyConfig | undefined = config.strategy_list?.[0]

  const indicatorLabels: Record<string, string> = {
    annual_return: '年化收益',
    sharpe_ratio: '夏普比率',
    max_drawdown: '最大回撤',
    win_rate: '胜率',
  }

  const formatValue = (key: string, value: number | undefined) => {
    if (value === undefined || value === null) return '-'
    if (key === 'sharpe_ratio') return value.toFixed(2)
    return `${(value * 100).toFixed(2)}%`
  }

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <BarChart3 className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold text-muted-foreground">参数敏感性分析</h3>
        {showConfigName && config_name && (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
            {config_name}
          </span>
        )}
        <span className={cn(
          "px-1.5 py-0.5 text-xs rounded",
          is2D ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700"
        )}>
          {is2D ? '热力图' : '柱状图'}
        </span>
        {updated_at && (
          <span className="text-xs text-muted-foreground">
            更新于 {new Date(updated_at).toLocaleDateString('zh-CN')}
          </span>
        )}
      </div>
      {showConfigName && description && (
        <p className="mb-3 text-xs text-muted-foreground">{description}</p>
      )}

      {/* Config */}
      <div className="mb-4 rounded-lg border bg-slate-50/50 p-4">
        <h4 className="text-xs font-medium text-muted-foreground mb-3">回测配置</h4>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">持仓周期</span>
            <span className="font-medium font-mono text-xs">{firstStrategy?.hold_period || '-'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">市场类型</span>
            <span className="font-medium font-mono text-xs">{firstStrategy?.market || '-'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">多头选币</span>
            <span className="font-medium font-mono text-xs">{firstStrategy?.long_select_coin_num ?? '-'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">空头选币</span>
            <span className="font-medium font-mono text-xs">{firstStrategy?.short_select_coin_num ?? '-'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">评价指标</span>
            <span className="font-medium">{indicatorLabels[indicator] || indicator}</span>
          </div>
        </div>

        <div className="mt-3 pt-3 border-t">
          <span className="text-xs text-muted-foreground">遍历参数:</span>
          <div className="mt-1 space-y-1">
            {grid_keys.map((key) => {
              const values = config.param_grid[key]
              return (
                <div key={key} className="flex items-center gap-2 text-xs">
                  <span className="font-mono bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded shrink-0">
                    {key}
                  </span>
                  <span className="text-muted-foreground">=</span>
                  <span className="font-mono text-slate-700">
                    [{values?.map(v => JSON.stringify(v)).join(', ')}]
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="mb-4 rounded-lg border bg-white p-2">
        <BaseChart
          option={chart as Parameters<typeof BaseChart>[0]['option']}
          style={{ height: is2D ? '360px' : '280px' }}
        />
      </div>

      {/* All Results */}
      {results && results.length > 0 && (
        <div className="rounded-lg border">
          <button
            onClick={() => setShowAllResults(!showAllResults)}
            className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium hover:bg-slate-50 transition-colors"
          >
            <span>全部参数结果 ({results.length})</span>
            <span className={cn("transition-transform", showAllResults && "rotate-180")}>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </span>
          </button>
          {showAllResults && (
            <div className="border-t overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    {grid_keys.map((key) => (
                      <th key={key} className="px-4 py-2 text-left font-medium text-muted-foreground whitespace-nowrap font-mono">
                        {key}
                      </th>
                    ))}
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">年化收益</th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">夏普比率</th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">最大回撤</th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">胜率</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((result, idx) => {
                    const isBest = grid_keys.every((key) => result[key] === best_result[key])
                    const rowKey = grid_keys.map((k) => result[k]).join('-') || idx
                    return (
                      <tr key={rowKey} className={cn("border-t", isBest && "bg-green-50")}>
                        {grid_keys.map((key) => (
                          <td key={key} className="px-4 py-2">
                            <span className={cn("font-medium", isBest && "text-green-700")}>
                              {String(result[key])}
                            </span>
                          </td>
                        ))}
                        <td className={cn(
                          "px-4 py-2 text-right",
                          result.annual_return !== undefined && (result.annual_return as number) < 0 && "text-red-600"
                        )}>
                          {result.error ? (
                            <span className="text-red-500 text-xs">{result.error}</span>
                          ) : (
                            formatValue('annual_return', result.annual_return as number | undefined)
                          )}
                        </td>
                        <td className={cn(
                          "px-4 py-2 text-right",
                          result.sharpe_ratio !== undefined && (result.sharpe_ratio as number) < 0 && "text-red-600"
                        )}>
                          {formatValue('sharpe_ratio', result.sharpe_ratio as number | undefined)}
                        </td>
                        <td className="px-4 py-2 text-right text-red-600">
                          {formatValue('max_drawdown', result.max_drawdown as number | undefined)}
                        </td>
                        <td className="px-4 py-2 text-right">
                          {formatValue('win_rate', result.win_rate as number | undefined)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
