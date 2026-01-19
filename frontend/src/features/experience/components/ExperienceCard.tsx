/**
 * Experience Card Component
 *
 * 展示单个经验的卡片组件
 * 简化版本: 以标签为核心管理
 */

import { memo } from 'react'
import { cn } from '@/lib/utils'
import { ChevronRight, Clock, Tag } from 'lucide-react'
import type { Experience } from '../types'

interface ExperienceCardProps {
  experience: Experience
  onClick?: () => void
  isSelected?: boolean
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

export const ExperienceCard = memo(function ExperienceCard({
  experience,
  onClick,
  isSelected = false,
}: ExperienceCardProps) {
  const tags = experience.context?.tags || []

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
          {/* 标题 */}
          <h3 className="font-medium text-base line-clamp-2">{experience.title}</h3>
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
        {/* 标签 */}
        {tags.length > 0 && (
          <div className="flex items-center gap-1">
            <Tag className="h-3 w-3" />
            {tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-muted px-2 py-0.5 text-xs"
              >
                {tag}
              </span>
            ))}
            {tags.length > 3 && (
              <span className="text-muted-foreground">
                +{tags.length - 3}
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
