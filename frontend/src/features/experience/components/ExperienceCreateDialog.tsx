/**
 * Experience Create Dialog Component
 *
 * 创建经验的对话框
 */

import { useState, useCallback } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'
import { useExperienceMutations } from '../hooks'
import type { ExperienceCreate, ExperienceLevel, SourceType } from '../types'
import {
  EXPERIENCE_LEVEL_LABELS,
  SOURCE_TYPE_LABELS,
  MARKET_REGIME_OPTIONS,
  TIME_HORIZON_OPTIONS,
  ASSET_CLASS_OPTIONS,
  CATEGORIES_BY_LEVEL,
  EXPERIENCE_CATEGORY_LABELS,
  DEFAULT_EXPERIENCE_CONTENT,
  DEFAULT_EXPERIENCE_CONTEXT,
  type ExperienceCategory,
} from '../types'

interface ExperienceCreateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: (experience: unknown) => void
}

// 层级选项
const LEVEL_OPTIONS: SelectOption[] = [
  { value: 'operational', label: EXPERIENCE_LEVEL_LABELS.operational },
  { value: 'tactical', label: EXPERIENCE_LEVEL_LABELS.tactical },
  { value: 'strategic', label: EXPERIENCE_LEVEL_LABELS.strategic },
]

// 来源类型选项
const SOURCE_TYPE_OPTIONS: SelectOption[] = [
  { value: 'manual', label: SOURCE_TYPE_LABELS.manual },
  { value: 'research', label: SOURCE_TYPE_LABELS.research },
  { value: 'backtest', label: SOURCE_TYPE_LABELS.backtest },
  { value: 'live_trade', label: SOURCE_TYPE_LABELS.live_trade },
  { value: 'external', label: SOURCE_TYPE_LABELS.external },
]

// 获取分类选项
function getCategoryOptions(level: ExperienceLevel): SelectOption[] {
  const categories = CATEGORIES_BY_LEVEL[level] || []
  return [
    { value: '', label: '选择分类' },
    ...categories.map((cat) => ({
      value: cat,
      label: EXPERIENCE_CATEGORY_LABELS[cat],
    })),
  ]
}

const initialFormData: ExperienceCreate = {
  title: '',
  experience_level: 'operational',
  category: '',
  content: { ...DEFAULT_EXPERIENCE_CONTENT },
  context: { ...DEFAULT_EXPERIENCE_CONTEXT },
  source_type: 'manual',
  source_ref: '',
  confidence: 0.5,
}

export function ExperienceCreateDialog({
  open,
  onOpenChange,
  onSuccess,
}: ExperienceCreateDialogProps) {
  const { createExperience } = useExperienceMutations()
  const [formData, setFormData] = useState<ExperienceCreate>(initialFormData)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'basic' | 'parl' | 'context'>('basic')

  const categoryOptions = getCategoryOptions(formData.experience_level || 'operational')

  const handleSubmit = useCallback(async () => {
    if (!formData.title?.trim()) {
      setError('请输入经验标题')
      return
    }
    if (!formData.content?.lesson?.trim()) {
      setError('请输入核心教训 (Lesson)')
      return
    }

    setError(null)
    try {
      const result = await createExperience.mutateAsync(formData)
      onOpenChange(false)
      setFormData(initialFormData)
      onSuccess?.(result)
    } catch (err) {
      setError((err as Error).message)
    }
  }, [formData, createExperience, onOpenChange, onSuccess])

  const updateFormData = useCallback((updates: Partial<ExperienceCreate>) => {
    setFormData((prev) => ({ ...prev, ...updates }))
  }, [])

  const updateContent = useCallback(
    (field: keyof typeof DEFAULT_EXPERIENCE_CONTENT, value: string) => {
      setFormData((prev) => ({
        ...prev,
        content: { ...prev.content!, [field]: value },
      }))
    },
    []
  )

  const updateContext = useCallback(
    (field: keyof typeof DEFAULT_EXPERIENCE_CONTEXT, value: string | string[]) => {
      setFormData((prev) => ({
        ...prev,
        context: { ...prev.context!, [field]: value },
      }))
    },
    []
  )

  const handleLevelChange = useCallback((level: string) => {
    setFormData((prev) => ({
      ...prev,
      experience_level: level as ExperienceLevel,
      category: '', // 重置分类
    }))
  }, [])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>创建新经验</DialogTitle>
          <DialogDescription>
            记录研究过程中的经验和教训，使用 PARL 框架（Problem-Approach-Result-Lesson）。
          </DialogDescription>
        </DialogHeader>

        {/* Tab Navigation */}
        <div className="flex border-b">
          <button
            type="button"
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              activeTab === 'basic'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setActiveTab('basic')}
          >
            基础信息
          </button>
          <button
            type="button"
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              activeTab === 'parl'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setActiveTab('parl')}
          >
            PARL 内容
          </button>
          <button
            type="button"
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              activeTab === 'context'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setActiveTab('context')}
          >
            上下文
          </button>
        </div>

        <div className="space-y-4 py-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* 基础信息 Tab */}
          {activeTab === 'basic' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">
                  经验标题 <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="title"
                  value={formData.title || ''}
                  onChange={(e) => updateFormData({ title: e.target.value })}
                  placeholder="简洁描述这条经验的核心内容"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>经验层级</Label>
                  <SearchableSelect
                    options={LEVEL_OPTIONS}
                    value={formData.experience_level || 'operational'}
                    onChange={handleLevelChange}
                  />
                </div>
                <div className="space-y-2">
                  <Label>分类</Label>
                  <SearchableSelect
                    options={categoryOptions}
                    value={formData.category || ''}
                    onChange={(value) => updateFormData({ category: value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>来源类型</Label>
                  <SearchableSelect
                    options={SOURCE_TYPE_OPTIONS}
                    value={formData.source_type || 'manual'}
                    onChange={(value) =>
                      updateFormData({ source_type: value as SourceType })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="source_ref">来源引用</Label>
                  <Input
                    id="source_ref"
                    value={formData.source_ref || ''}
                    onChange={(e) => updateFormData({ source_ref: e.target.value })}
                    placeholder="如：研究会话 ID、回测任务 ID"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confidence">
                  初始置信度: {Math.round((formData.confidence || 0.5) * 100)}%
                </Label>
                <input
                  type="range"
                  id="confidence"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.confidence || 0.5}
                  onChange={(e) =>
                    updateFormData({ confidence: parseFloat(e.target.value) })
                  }
                  className="w-full"
                />
              </div>
            </div>
          )}

          {/* PARL 内容 Tab */}
          {activeTab === 'parl' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="problem">Problem (问题)</Label>
                <Textarea
                  id="problem"
                  value={formData.content?.problem || ''}
                  onChange={(e) => updateContent('problem', e.target.value)}
                  placeholder="面临的问题或挑战是什么？"
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="approach">Approach (方法)</Label>
                <Textarea
                  id="approach"
                  value={formData.content?.approach || ''}
                  onChange={(e) => updateContent('approach', e.target.value)}
                  placeholder="采用了什么方法或策略来解决？"
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="result">Result (结果)</Label>
                <Textarea
                  id="result"
                  value={formData.content?.result || ''}
                  onChange={(e) => updateContent('result', e.target.value)}
                  placeholder="得到了什么结果？"
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="lesson">
                  Lesson (教训) <span className="text-destructive">*</span>
                </Label>
                <Textarea
                  id="lesson"
                  value={formData.content?.lesson || ''}
                  onChange={(e) => updateContent('lesson', e.target.value)}
                  placeholder="总结出的教训或规律是什么？这是最重要的部分。"
                  rows={4}
                  className="border-primary/50"
                />
              </div>
            </div>
          )}

          {/* 上下文 Tab */}
          {activeTab === 'context' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>市场环境</Label>
                  <SearchableSelect
                    options={MARKET_REGIME_OPTIONS}
                    value={formData.context?.market_regime || ''}
                    onChange={(value) => updateContext('market_regime', value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>时间范围</Label>
                  <SearchableSelect
                    options={TIME_HORIZON_OPTIONS}
                    value={formData.context?.time_horizon || ''}
                    onChange={(value) => updateContext('time_horizon', value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>资产类别</Label>
                <SearchableSelect
                  options={ASSET_CLASS_OPTIONS}
                  value={formData.context?.asset_class || ''}
                  onChange={(value) => updateContext('asset_class', value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="factor_styles">因子风格（逗号分隔）</Label>
                <Input
                  id="factor_styles"
                  value={formData.context?.factor_styles?.join(', ') || ''}
                  onChange={(e) =>
                    updateContext(
                      'factor_styles',
                      e.target.value
                        .split(',')
                        .map((s) => s.trim())
                        .filter(Boolean)
                    )
                  }
                  placeholder="如：动量, 反转, 波动率"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="tags">标签（逗号分隔）</Label>
                <Input
                  id="tags"
                  value={formData.context?.tags?.join(', ') || ''}
                  onChange={(e) =>
                    updateContext(
                      'tags',
                      e.target.value
                        .split(',')
                        .map((s) => s.trim())
                        .filter(Boolean)
                    )
                  }
                  placeholder="自定义标签，用于快速检索"
                />
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={createExperience.isPending}>
            {createExperience.isPending ? '创建中...' : '创建经验'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
