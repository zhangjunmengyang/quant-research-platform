/**
 * Experience Card Component
 *
 * 展示单个经验的卡片组件
 */

import { memo } from 'react'
import { cn } from '@/lib/utils'
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  ChevronRight,
  Target,
  Lightbulb,
  FileText,
} from 'lucide-react'
import type { Experience, ExperienceLevel, ExperienceStatus } from '../types'
import {
  EXPERIENCE_LEVEL_LABELS,
  EXPERIENCE_STATUS_LABELS,
  EXPERIENCE_STATUS_COLORS,
  EXPERIENCE_CATEGORY_LABELS,
  type ExperienceCategory,
} from '../types'

interface ExperienceCardProps {
  experience: Experience
  onClick?: () => void
  isSelected?: boolean
  showActions?: boolean
}

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
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

function formatConfidence(confidence: number) {
  return `${Math.round(confidence * 100)}%`
}

export const ExperienceCard = memo(function ExperienceCard({
  experience,
  onClick,
  isSelected = false,
}: ExperienceCardProps) {
  const LevelIcon = LEVEL_ICONS[experience.experience_level]
  const StatusIcon = STATUS_ICONS[experience.status]
  const statusColorClass = EXPERIENCE_STATUS_COLORS[experience.status]

  const categoryLabel =
    EXPERIENCE_CATEGORY_LABELS[experience.category as ExperienceCategory] || experience.category

  return (
    <div
      onClick={onClick}
      className={cn(
        'group cursor-pointer rounded-lg border p-4 transition-all hover:shadow-md',
        isSelected ? 'border-primary bg-primary/5 ring-1 ring-primary' : 'hover:bg-muted/50'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {/* 层级标签 */}
            <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium bg-secondary text-secondary-foreground">
              <LevelIcon className="h-3 w-3" />
              {EXPERIENCE_LEVEL_LABELS[experience.experience_level]}
            </span>
            {/* 状态标签 */}
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

          {/* 标题 */}
          <h3 className="font-medium text-base line-clamp-2">{experience.title}</h3>

          {/* 分类 */}
          {categoryLabel && (
            <p className="text-xs text-muted-foreground mt-1">{categoryLabel}</p>
          )}
        </div>

        {/* 箭头 */}
        <ChevronRight className="h-5 w-5 text-muted-foreground/50 group-hover:text-muted-foreground transition-colors flex-shrink-0" />
      </div>

      {/* PARL 内容预览 */}
      {experience.content && (
        <div className="mt-3 space-y-1">
          {experience.content.lesson && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              <span className="font-medium text-foreground">Lesson: </span>
              {experience.content.lesson}
            </p>
          )}
          {!experience.content.lesson && experience.content.result && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              <span className="font-medium text-foreground">Result: </span>
              {experience.content.result}
            </p>
          )}
        </div>
      )}

      {/* 底部信息 */}
      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        {/* 置信度 */}
        <div className="flex items-center gap-1">
          <span className="font-medium">置信度:</span>
          <span
            className={cn(
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

        {/* 验证次数 */}
        {experience.validation_count > 0 && (
          <div className="flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            <span>验证 {experience.validation_count} 次</span>
          </div>
        )}

        {/* 上下文标签 */}
        {experience.context?.tags && experience.context.tags.length > 0 && (
          <div className="flex items-center gap-1">
            {experience.context.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-muted px-2 py-0.5 text-xs"
              >
                {tag}
              </span>
            ))}
            {experience.context.tags.length > 3 && (
              <span className="text-muted-foreground">
                +{experience.context.tags.length - 3}
              </span>
            )}
          </div>
        )}

        {/* 更新时间 */}
        <div className="ml-auto flex items-center gap-1">
          <Clock className="h-3 w-3" />
          <span>{formatDate(experience.updated_at)}</span>
        </div>
      </div>
    </div>
  )
})
