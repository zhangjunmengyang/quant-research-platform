/**
 * Node Preview Card Component
 * 节点预览卡片组件 - 点击节点时显示基本信息
 */

import { useRef, useEffect, useCallback } from 'react'
import { X, ExternalLink, Maximize2, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { NODE_TYPE_CONFIG, parseNodeKey } from '../types'
import { useEntityTags } from '../hooks'

interface NodePreviewCardProps {
  nodeKey: string // 格式: type:id
  position: { x: number; y: number }
  containerRect: DOMRect | null // 容器边界，用于计算卡片位置
  onClose: () => void
  onViewDetail: () => void
  onExpandInGraph?: () => void // 可选，在图谱中展开
}

const CARD_WIDTH = 260
const CARD_HEIGHT_ESTIMATE = 180 // 估算高度，用于边界检测
const OFFSET = 12 // 与点击位置的偏移

export function NodePreviewCard({
  nodeKey,
  position,
  containerRect,
  onClose,
  onViewDetail,
  onExpandInGraph,
}: NodePreviewCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const { type, id } = parseNodeKey(nodeKey)
  const config = NODE_TYPE_CONFIG[type]

  // 获取标签数据
  const { data: tagsData, isLoading } = useEntityTags(type, id)

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (cardRef.current && !cardRef.current.contains(e.target as Node)) {
        onClose()
      }
    }

    // 延迟添加事件监听，避免立即触发
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside)
    }, 0)

    return () => {
      clearTimeout(timer)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [onClose])

  // ESC 关闭
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  // 计算卡片位置
  const cardStyle = useCallback((): React.CSSProperties => {
    if (!containerRect) {
      return { left: position.x + OFFSET, top: position.y + OFFSET }
    }

    let left = position.x + OFFSET
    let top = position.y + OFFSET

    // 检查右边界
    if (left + CARD_WIDTH > containerRect.width) {
      left = position.x - CARD_WIDTH - OFFSET
    }

    // 检查下边界
    if (top + CARD_HEIGHT_ESTIMATE > containerRect.height) {
      top = position.y - CARD_HEIGHT_ESTIMATE - OFFSET
    }

    // 确保不超出左边界
    if (left < 0) {
      left = OFFSET
    }

    // 确保不超出上边界
    if (top < 0) {
      top = OFFSET
    }

    return { left, top }
  }, [position, containerRect])

  // 格式化显示名称
  const displayName = type === 'factor' && id.endsWith('.py') ? id.slice(0, -3) : id

  return (
    <div
      ref={cardRef}
      className="absolute z-50 bg-popover border rounded-lg shadow-lg overflow-hidden"
      style={{ ...cardStyle(), width: CARD_WIDTH }}
    >
      {/* 头部 */}
      <div className="flex items-center justify-between px-3 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <span
            className="px-2 py-0.5 text-xs rounded-full text-white"
            style={{ backgroundColor: config?.color }}
          >
            {config?.label || type}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded hover:bg-muted transition-colors"
        >
          <X className="h-3.5 w-3.5 text-muted-foreground" />
        </button>
      </div>

      {/* 内容 */}
      <div className="p-3">
        {/* 名称 */}
        <h4 className="font-medium text-sm mb-2 break-all">{displayName}</h4>

        {/* 标签 */}
        <div className="mb-3">
          <span className="text-xs text-muted-foreground">标签:</span>
          {isLoading ? (
            <div className="flex items-center gap-1 mt-1">
              <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
              <span className="text-xs text-muted-foreground">加载中...</span>
            </div>
          ) : tagsData?.tags && tagsData.tags.length > 0 ? (
            <div className="flex flex-wrap gap-1 mt-1">
              {tagsData.tags.slice(0, 5).map((tag) => (
                <span
                  key={tag}
                  className="px-1.5 py-0.5 text-xs bg-muted rounded"
                >
                  {tag}
                </span>
              ))}
              {tagsData.tags.length > 5 && (
                <span className="text-xs text-muted-foreground">
                  +{tagsData.tags.length - 5}
                </span>
              )}
            </div>
          ) : (
            <span className="text-xs text-muted-foreground ml-1">无</span>
          )}
        </div>

        {/* 操作按钮 */}
        <div className="flex items-center gap-2">
          <Button
            variant="default"
            size="sm"
            className="h-7 text-xs flex-1"
            onClick={onViewDetail}
          >
            <ExternalLink className="h-3 w-3 mr-1" />
            查看详情
          </Button>
          {onExpandInGraph && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs flex-1"
              onClick={onExpandInGraph}
            >
              <Maximize2 className="h-3 w-3 mr-1" />
              展开
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
