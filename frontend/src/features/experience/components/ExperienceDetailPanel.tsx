/**
 * Experience Detail Panel Component
 *
 * 经验详情侧边面板
 * 简化版本: 以标签为核心管理
 */

import { useState } from 'react'
import { createPortal } from 'react-dom'
import {
  X,
  Clock,
  Edit2,
  Trash2,
  Tag,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EntityGraph } from '@/features/graph'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { useExperienceDetail } from '../hooks'
import { useExperienceStore } from '../store'
import type { Experience } from '../types'

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
  const { deleteExperience } = useExperienceDetail(experience.id)

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const tags = experience.context?.tags || []

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
        {/* 标题 */}
        <div>
          <h3 className="text-xl font-semibold">{experience.title}</h3>
          {/* 标签 */}
          {tags.length > 0 && (
            <div className="flex items-center gap-1 mt-2 flex-wrap">
              <Tag className="h-3 w-3 text-muted-foreground" />
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-muted px-2 py-0.5 text-xs"
                >
                  {tag}
                </span>
              ))}
            </div>
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

        {/* 知识关联图 */}
        {experience.uuid && (
          <EntityGraph
            entityType="experience"
            entityId={experience.uuid}
            entityName={experience.title}
            height={200}
          />
        )}

        {/* 时间信息 */}
        <div className="space-y-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            创建时间: {formatDate(experience.created_at)}
          </div>
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            更新时间: {formatDate(experience.updated_at)}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="border-t p-4 space-y-2">
        {onEdit && (
          <Button variant="outline" size="sm" className="w-full" onClick={onEdit}>
            <Edit2 className="h-4 w-4 mr-1" />
            编辑
          </Button>
        )}
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

      {/* Delete Confirm Dialog */}
      <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p className="py-4 text-sm text-muted-foreground">
            确定要删除经验「{experience.title}」吗?此操作无法撤销。
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
 * 使用 createPortal 渲染到 document.body，确保侧栏覆盖全屏高度
 */
export function ExperienceDetailPanelWrapper() {
  const { selectedExperience, detailPanelOpen, closeDetailPanel } = useExperienceStore()

  if (!detailPanelOpen || !selectedExperience) {
    return null
  }

  return createPortal(
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/50"
        onClick={closeDetailPanel}
      />
      {/* Panel */}
      <div className="fixed inset-y-0 right-0 z-50 w-[480px] border-l bg-background shadow-lg">
        <ExperienceDetailPanel experience={selectedExperience} onClose={closeDetailPanel} />
      </div>
    </>,
    document.body
  )
}
