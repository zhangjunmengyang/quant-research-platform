/**
 * RelationEditor - 关系编辑器组件
 *
 * 功能:
 * - 显示实体的所有关联
 * - 添加新关联
 * - 删除现有关联
 * - 自动创建的关联显示标记
 */

import { useState } from 'react'
import { Plus, Trash2, Check, X, Link2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { useEntityEdges, useCreateLink, useDeleteLink } from '../hooks'
import {
  NODE_TYPE_CONFIG,
  SUBTYPE_LABELS,
  type GraphNodeType,
  type GraphRelationType,
  type GraphEdge,
} from '../types'

interface RelationEditorProps {
  entityType: GraphNodeType
  entityId: string
  onRelationChange?: () => void
}

const EDITABLE_NODE_TYPES: GraphNodeType[] = [
  'factor',
  'strategy',
  'note',
  'research',
  'experience',
]

const DERIVE_SUBTYPES = ['based', 'inspired', 'uses', 'produces', 'evolves', 'enables']
const RELATE_SUBTYPES = ['refs', 'similar', 'validates', 'contrasts', 'temporal']

export function RelationEditor({
  entityType,
  entityId,
  onRelationChange,
}: RelationEditorProps) {
  const { data: edgesData, refetch, isLoading } = useEntityEdges(entityType, entityId)
  const createLink = useCreateLink()
  const deleteLink = useDeleteLink()

  const [isAdding, setIsAdding] = useState(false)
  const [newRelation, setNewRelation] = useState({
    targetType: 'factor' as GraphNodeType,
    targetId: '',
    relation: 'relates' as GraphRelationType,
    subtype: '',
  })

  const handleAdd = async () => {
    if (!newRelation.targetId.trim()) return

    try {
      await createLink.mutateAsync({
        sourceType: entityType,
        sourceId: entityId,
        targetType: newRelation.targetType,
        targetId: newRelation.targetId.trim(),
        relation: newRelation.relation,
        subtype: newRelation.subtype,
      })

      setIsAdding(false)
      setNewRelation({
        targetType: 'factor',
        targetId: '',
        relation: 'relates',
        subtype: '',
      })
      refetch()
      onRelationChange?.()
    } catch (error) {
      console.error('创建关联失败:', error)
    }
  }

  const handleDelete = async (edge: GraphEdge) => {
    try {
      await deleteLink.mutateAsync({
        sourceType: edge.source_type,
        sourceId: edge.source_id,
        targetType: edge.target_type,
        targetId: edge.target_id,
        relation: edge.relation,
      })
      refetch()
      onRelationChange?.()
    } catch (error) {
      console.error('删除关联失败:', error)
    }
  }

  const subtypeOptions = newRelation.relation === 'derives' ? DERIVE_SUBTYPES : RELATE_SUBTYPES

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Link2 className="h-4 w-4 text-muted-foreground" />
          <h4 className="text-sm font-medium">关联管理</h4>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsAdding(true)}
          disabled={isAdding}
        >
          <Plus className="h-4 w-4 mr-1" />
          添加关联
        </Button>
      </div>

      {/* 添加表单 */}
      {isAdding && (
        <div className="p-4 border rounded-lg space-y-3 bg-muted/30">
          <div className="grid grid-cols-2 gap-3">
            <select
              value={newRelation.targetType}
              onChange={(e) =>
                setNewRelation({ ...newRelation, targetType: e.target.value as GraphNodeType })
              }
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              {EDITABLE_NODE_TYPES.map((type) => (
                <option key={type} value={type}>
                  {NODE_TYPE_CONFIG[type].label}
                </option>
              ))}
            </select>
            <Input
              placeholder="目标实体 ID"
              value={newRelation.targetId}
              onChange={(e) =>
                setNewRelation({ ...newRelation, targetId: e.target.value })
              }
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <select
              value={newRelation.relation}
              onChange={(e) =>
                setNewRelation({
                  ...newRelation,
                  relation: e.target.value as GraphRelationType,
                  subtype: '', // 切换关系类型时重置子类型
                })
              }
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="derives">派生 (derives)</option>
              <option value="relates">关联 (relates)</option>
            </select>
            <select
              value={newRelation.subtype}
              onChange={(e) => setNewRelation({ ...newRelation, subtype: e.target.value })}
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="">子类型 (可选)</option>
              {subtypeOptions.map((st) => (
                <option key={st} value={st}>
                  {SUBTYPE_LABELS[st] || st}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setIsAdding(false)
                setNewRelation({
                  targetType: 'factor',
                  targetId: '',
                  relation: 'relates',
                  subtype: '',
                })
              }}
            >
              <X className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              onClick={handleAdd}
              disabled={!newRelation.targetId.trim() || createLink.isPending}
            >
              <Check className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* 关联列表 */}
      <div className="space-y-2">
        {isLoading ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            加载中...
          </p>
        ) : edgesData?.edges && edgesData.edges.length > 0 ? (
          edgesData.edges.map((edge, idx) => {
            const isOutgoing =
              edge.source_type === entityType && edge.source_id === entityId
            const otherType = isOutgoing ? edge.target_type : edge.source_type
            const otherId = isOutgoing ? edge.target_id : edge.source_id
            const metadata = edge.metadata as Record<string, unknown> | undefined
            const isAutoExtracted = metadata?.auto_extracted === true

            return (
              <div
                key={idx}
                className="flex items-center justify-between p-2 border rounded hover:bg-muted/50"
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <Badge
                    variant="outline"
                    style={{
                      borderColor: NODE_TYPE_CONFIG[otherType]?.color,
                      color: NODE_TYPE_CONFIG[otherType]?.color,
                    }}
                  >
                    {NODE_TYPE_CONFIG[otherType]?.label}
                  </Badge>
                  <span className="text-sm font-mono truncate" title={otherId}>
                    {otherId.replace('.py', '')}
                  </span>
                  <span className="text-xs text-muted-foreground shrink-0">
                    {isOutgoing ? '->' : '<-'}{' '}
                    {edge.subtype ? SUBTYPE_LABELS[edge.subtype] || edge.subtype : edge.relation}
                  </span>
                  {isAutoExtracted && (
                    <Badge variant="secondary" className="text-xs shrink-0">
                      自动
                    </Badge>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive hover:text-destructive shrink-0"
                  onClick={() => handleDelete(edge)}
                  disabled={deleteLink.isPending}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            )
          })
        ) : (
          <p className="text-sm text-muted-foreground text-center py-4">
            暂无关联
          </p>
        )}
      </div>
    </div>
  )
}
