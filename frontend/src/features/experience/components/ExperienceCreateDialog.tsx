/**
 * Experience Create Dialog Component
 *
 * 创建经验的对话框
 * 简化版本: 以标签为核心管理
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
import { useExperienceMutations } from '../hooks'
import type { ExperienceCreate } from '../types'
import {
  DEFAULT_EXPERIENCE_CONTENT,
} from '../types'

interface ExperienceCreateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: (experience: unknown) => void
}

const initialFormData: ExperienceCreate = {
  title: '',
  content: { ...DEFAULT_EXPERIENCE_CONTENT },
  context: {
    tags: [],
  },
}

export function ExperienceCreateDialog({
  open,
  onOpenChange,
  onSuccess,
}: ExperienceCreateDialogProps) {
  const { createExperience } = useExperienceMutations()
  const [formData, setFormData] = useState<ExperienceCreate>(initialFormData)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'basic' | 'parl'>('basic')

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

  const updateTags = useCallback((value: string) => {
    const tags = value
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    setFormData((prev) => ({
      ...prev,
      context: { ...prev.context, tags },
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

              <div className="space-y-2">
                <Label htmlFor="tags">标签（逗号分隔）</Label>
                <Input
                  id="tags"
                  value={formData.context?.tags?.join(', ') || ''}
                  onChange={(e) => updateTags(e.target.value)}
                  placeholder="自定义标签，用于快速检索，如: 动量, 反转, 震荡市"
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
                  placeholder="面临的问题或挑战是什么?"
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="approach">Approach (方法)</Label>
                <Textarea
                  id="approach"
                  value={formData.content?.approach || ''}
                  onChange={(e) => updateContent('approach', e.target.value)}
                  placeholder="采用了什么方法或策略来解决?"
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="result">Result (结果)</Label>
                <Textarea
                  id="result"
                  value={formData.content?.result || ''}
                  onChange={(e) => updateContent('result', e.target.value)}
                  placeholder="得到了什么结果?"
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
                  placeholder="总结出的教训或规律是什么?这是最重要的部分。"
                  rows={4}
                  className="border-primary/50"
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
