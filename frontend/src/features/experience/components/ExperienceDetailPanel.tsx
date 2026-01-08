/**
 * Experience Detail Panel Component
 *
 * 经验详情侧边面板
 */

import { useState } from 'react'
import { cn } from '@/lib/utils'
import {
  X,
  CheckCircle2,
  Clock,
  AlertCircle,
  Target,
  Lightbulb,
  FileText,
  Link2,
  Edit2,
  Trash2,
  ThumbsUp,
  Ban,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { useExperienceDetail, useExperienceLinks } from '../hooks'
import { useExperienceStore } from '../store'
import type { Experience, ExperienceLevel, ExperienceStatus } from '../types'
import {
  EXPERIENCE_LEVEL_LABELS,
  EXPERIENCE_LEVEL_DESCRIPTIONS,
  EXPERIENCE_STATUS_LABELS,
  EXPERIENCE_STATUS_COLORS,
  EXPERIENCE_CATEGORY_LABELS,
  SOURCE_TYPE_LABELS,
  type ExperienceCategory,
  type SourceType,
} from '../types'

// 层级图标映射
const LEVEL_ICONS: Record<ExperienceLevel, React.ComponentType<{ className?: string }>> = {
  strategic: Target,
  tactical: Lightbulb,
  operational: FileText,
}

// 状态图标映射
const STATUS_ICONS: Record<ExperienceStatus, React.ComponentType<{ className?: string }>> = {
  draft: Clock,
  validated: CheckCircle2,
  deprecated: AlertCircle,
}

function formatDate(dateStr?: string) {
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

function formatConfidence(confidence: number) {
  return `${Math.round(confidence * 100)}%`
}

interface ExperienceDetailPanelProps {
  experience: Experience
  onClose: () => void
  onEdit?: () => void
}

export function ExperienceDetailPanel({
  experience,
  onClose,
  onEdit,
}: ExperienceDetailPanelProps) {
  const { validateExperience, deprecateExperience, deleteExperience } = useExperienceDetail(
    experience.id
  )
  const { data: links = [] } = useExperienceLinks(experience.id)

  const [showDeprecateDialog, setShowDeprecateDialog] = useState(false)
  const [deprecateReason, setDeprecateReason] = useState('')
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const LevelIcon = LEVEL_ICONS[experience.experience_level]
  const StatusIcon = STATUS_ICONS[experience.status]
  const statusColorClass = EXPERIENCE_STATUS_COLORS[experience.status]
  const categoryLabel =
    EXPERIENCE_CATEGORY_LABELS[experience.category as ExperienceCategory] || experience.category
  const sourceLabel =
    SOURCE_TYPE_LABELS[experience.source_type as SourceType] || experience.source_type

  const handleValidate = async () => {
    try {
      await validateExperience.mutateAsync({ id: experience.id })
    } catch (err) {
      console.error('Validate failed:', err)
    }
  }

  const handleDeprecate = async () => {
    if (!deprecateReason.trim()) return
    try {
      await deprecateExperience.mutateAsync({
        id: experience.id,
        request: { reason: deprecateReason },
      })
      setShowDeprecateDialog(false)
      setDeprecateReason('')
    } catch (err) {
      console.error('Deprecate failed:', err)
    }
  }

  const handleDelete = async () => {
    try {
      await deleteExperience.mutateAsync(experience.id)
      setShowDeleteConfirm(false)
      onClose()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Header */}
      <div className="flex items-center justify-between border-b p-4">
        <h2 className="text-lg font-semibold">经验详情</h2>
        <button
          onClick={onClose}
          className="rounded-md p-1 hover:bg-muted"
          aria-label="关闭"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4 space-y-6">
        {/* 标题和状态 */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium bg-secondary text-secondary-foreground">
              <LevelIcon className="h-3 w-3" />
              {EXPERIENCE_LEVEL_LABELS[experience.experience_level]}
            </span>
            <span
              className={cn(
                'inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium',
                statusColorClass
              )}
            >
              <StatusIcon className="h-3 w-3" />
              {EXPERIENCE_STATUS_LABELS[experience.status]}
            </span>
          </div>
          <h3 className="text-xl font-semibold">{experience.title}</h3>
          {categoryLabel && (
            <p className="text-sm text-muted-foreground mt-1">{categoryLabel}</p>
          )}
        </div>

        {/* PARL 内容 */}
        <div className="space-y-4">
          <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
            PARL 框架
          </h4>

          {experience.content?.problem && (
            <div className="rounded-lg border p-3">
              <div className="text-xs font-medium text-muted-foreground mb-1">Problem (问题)</div>
              <p className="text-sm whitespace-pre-wrap">{experience.content.problem}</p>
            </div>
          )}

          {experience.content?.approach && (
            <div className="rounded-lg border p-3">
              <div className="text-xs font-medium text-muted-foreground mb-1">Approach (方法)</div>
              <p className="text-sm whitespace-pre-wrap">{experience.content.approach}</p>
            </div>
          )}

          {experience.content?.result && (
            <div className="rounded-lg border p-3">
              <div className="text-xs font-medium text-muted-foreground mb-1">Result (结果)</div>
              <p className="text-sm whitespace-pre-wrap">{experience.content.result}</p>
            </div>
          )}

          {experience.content?.lesson && (
            <div className="rounded-lg border p-3 bg-primary/5 border-primary/20">
              <div className="text-xs font-medium text-primary mb-1">Lesson (教训)</div>
              <p className="text-sm whitespace-pre-wrap">{experience.content.lesson}</p>
            </div>
          )}
        </div>

        {/* 上下文信息 */}
        {experience.context && (
          <div className="space-y-3">
            <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
              上下文
            </h4>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {experience.context.market_regime && (
                <div>
                  <span className="text-muted-foreground">市场环境: </span>
                  <span>{experience.context.market_regime}</span>
                </div>
              )}
              {experience.context.time_horizon && (
                <div>
                  <span className="text-muted-foreground">时间范围: </span>
                  <span>{experience.context.time_horizon}</span>
                </div>
              )}
              {experience.context.asset_class && (
                <div>
                  <span className="text-muted-foreground">资产类别: </span>
                  <span>{experience.context.asset_class}</span>
                </div>
              )}
              {experience.context.factor_styles && experience.context.factor_styles.length > 0 && (
                <div className="col-span-2">
                  <span className="text-muted-foreground">因子风格: </span>
                  <span>{experience.context.factor_styles.join(', ')}</span>
                </div>
              )}
              {experience.context.tags && experience.context.tags.length > 0 && (
                <div className="col-span-2">
                  <span className="text-muted-foreground">标签: </span>
                  <div className="inline-flex flex-wrap gap-1 mt-1">
                    {experience.context.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full bg-muted px-2 py-0.5 text-xs"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 指标信息 */}
        <div className="space-y-3">
          <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
            指标
          </h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-muted-foreground">置信度: </span>
              <span
                className={cn(
                  'font-medium',
                  experience.confidence >= 0.7
                    ? 'text-green-600'
                    : experience.confidence >= 0.4
                      ? 'text-yellow-600'
                      : 'text-red-600'
                )}
              >
                {formatConfidence(experience.confidence)}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">验证次数: </span>
              <span>{experience.validation_count}</span>
            </div>
            <div>
              <span className="text-muted-foreground">来源: </span>
              <span>{sourceLabel}</span>
            </div>
            {experience.source_ref && (
              <div>
                <span className="text-muted-foreground">来源引用: </span>
                <span className="font-mono text-xs">{experience.source_ref}</span>
              </div>
            )}
          </div>
        </div>

        {/* 关联实体 */}
        {links.length > 0 && (
          <div className="space-y-3">
            <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide flex items-center gap-1">
              <Link2 className="h-4 w-4" />
              关联实体
            </h4>
            <div className="space-y-2">
              {links.map((link) => (
                <div
                  key={link.id}
                  className="flex items-center gap-2 text-sm rounded-md border p-2"
                >
                  <span className="text-muted-foreground">{link.entity_type}:</span>
                  <span className="font-mono text-xs">{link.entity_id}</span>
                  <span className="text-xs text-muted-foreground">({link.relation})</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 废弃原因 */}
        {experience.status === 'deprecated' && experience.deprecated_reason && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3">
            <div className="text-xs font-medium text-destructive mb-1">废弃原因</div>
            <p className="text-sm">{experience.deprecated_reason}</p>
          </div>
        )}

        {/* 时间信息 */}
        <div className="space-y-2 text-xs text-muted-foreground">
          <div>创建时间: {formatDate(experience.created_at)}</div>
          <div>更新时间: {formatDate(experience.updated_at)}</div>
          {experience.last_validated && (
            <div>最后验证: {formatDate(experience.last_validated)}</div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="border-t p-4 space-y-2">
        <div className="flex gap-2">
          {experience.status !== 'deprecated' && (
            <>
              <Button
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={handleValidate}
                disabled={validateExperience.isPending}
              >
                {validateExperience.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <ThumbsUp className="h-4 w-4 mr-1" />
                )}
                验证
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={() => setShowDeprecateDialog(true)}
              >
                <Ban className="h-4 w-4 mr-1" />
                废弃
              </Button>
            </>
          )}
          {onEdit && (
            <Button variant="outline" size="sm" className="flex-1" onClick={onEdit}>
              <Edit2 className="h-4 w-4 mr-1" />
              编辑
            </Button>
          )}
        </div>
        <Button
          variant="destructive"
          size="sm"
          className="w-full"
          onClick={() => setShowDeleteConfirm(true)}
        >
          <Trash2 className="h-4 w-4 mr-1" />
          删除
        </Button>
      </div>

      {/* Deprecate Dialog */}
      <Dialog open={showDeprecateDialog} onOpenChange={setShowDeprecateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>废弃经验</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <label className="text-sm font-medium">废弃原因</label>
            <textarea
              value={deprecateReason}
              onChange={(e) => setDeprecateReason(e.target.value)}
              placeholder="请输入废弃此经验的原因..."
              className="mt-2 w-full rounded-md border px-3 py-2 text-sm resize-none"
              rows={4}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeprecateDialog(false)}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeprecate}
              disabled={!deprecateReason.trim() || deprecateExperience.isPending}
            >
              {deprecateExperience.isPending ? '处理中...' : '确认废弃'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p className="py-4 text-sm text-muted-foreground">
            确定要删除经验「{experience.title}」吗？此操作无法撤销。
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteConfirm(false)}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteExperience.isPending}
            >
              {deleteExperience.isPending ? '删除中...' : '确认删除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

/**
 * 包装组件，使用 store 管理状态
 */
export function ExperienceDetailPanelWrapper() {
  const { selectedExperience, detailPanelOpen, closeDetailPanel } = useExperienceStore()

  if (!detailPanelOpen || !selectedExperience) {
    return null
  }

  return (
    <div className="fixed right-0 top-0 z-50 h-screen w-[480px] border-l shadow-lg">
      <ExperienceDetailPanel experience={selectedExperience} onClose={closeDetailPanel} />
    </div>
  )
}
