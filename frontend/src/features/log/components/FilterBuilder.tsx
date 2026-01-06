/**
 * FilterBuilder Component
 * 日志高级筛选构建器 - 支持多条件、多操作符筛选
 */

import { useState, useCallback, useMemo } from 'react'
import { Plus, Trash2, GripVertical } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'
import { cn } from '@/lib/utils'
import type { LogFilterCondition, FilterOperator } from '../types'

// 操作符选项
const OPERATOR_OPTIONS: SelectOption[] = [
  { value: '=', label: '=' },
  { value: '!=', label: '!=' },
  { value: '>', label: '>' },
  { value: '>=', label: '>=' },
  { value: '<', label: '<' },
  { value: '<=', label: '<=' },
  { value: 'like', label: 'like' },
  { value: 'not_like', label: 'not like' },
  { value: 'exist', label: 'exist' },
  { value: 'not_exist', label: 'not exist' },
]

// 基础字段选项
const BASE_FIELD_OPTIONS: SelectOption[] = [
  { value: 'timestamp', label: 'timestamp', group: '基础字段' },
  { value: 'topic', label: 'topic', group: '基础字段' },
  { value: 'level', label: 'level', group: '基础字段' },
  { value: 'logger', label: 'logger', group: '基础字段' },
  { value: 'trace_id', label: 'trace_id', group: '基础字段' },
  { value: 'message', label: 'message', group: '基础字段' },
  { value: 'data.system_prompt', label: 'system_prompt', group: '基础字段' },
  { value: 'data.user_prompt', label: 'user_prompt', group: '基础字段' },
]

interface FilterBuilderProps {
  filters: LogFilterCondition[]
  onChange: (filters: LogFilterCondition[]) => void
  availableFields?: string[]
  className?: string
}

// 生成唯一 ID
function generateId(): string {
  return `filter_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

export function FilterBuilder({
  filters,
  onChange,
  availableFields = [],
  className,
}: FilterBuilderProps) {
  // 构建字段选项（基础字段 + data.* 字段）
  const fieldOptions = useMemo(() => {
    const dataFields = availableFields
      .filter((f) => f.startsWith('data.'))
      .map((f) => ({
        value: f,
        label: f.replace('data.', ''),
        group: '扩展字段',
      }))
    return [...BASE_FIELD_OPTIONS, ...dataFields]
  }, [availableFields])

  // 添加新筛选条件
  const handleAddFilter = useCallback(() => {
    const newFilter: LogFilterCondition = {
      id: generateId(),
      field: '',
      operator: '=',
      value: '',
    }
    onChange([...filters, newFilter])
  }, [filters, onChange])

  // 删除筛选条件
  const handleRemoveFilter = useCallback(
    (id: string) => {
      onChange(filters.filter((f) => f.id !== id))
    },
    [filters, onChange]
  )

  // 更新筛选条件
  const handleUpdateFilter = useCallback(
    (id: string, updates: Partial<LogFilterCondition>) => {
      onChange(
        filters.map((f) => (f.id === id ? { ...f, ...updates } : f))
      )
    },
    [filters, onChange]
  )

  // 判断操作符是否需要值输入
  const operatorNeedsValue = (op: FilterOperator): boolean => {
    return op !== 'exist' && op !== 'not_exist'
  }

  return (
    <div className={cn('space-y-0', className)}>
      {/* 筛选条件列表 - 无边框设计 */}
      {filters.map((filter, index) => (
        <div
          key={filter.id}
          className="flex items-center gap-2 py-1.5"
        >
          {/* 拖拽手柄（预留） */}
          <div className="cursor-grab text-muted-foreground/40 hover:text-muted-foreground">
            <GripVertical className="h-4 w-4" />
          </div>

          {/* 字段选择 */}
          <div className="w-[160px] shrink-0">
            <SearchableSelect
              options={fieldOptions}
              value={filter.field}
              onChange={(value) => handleUpdateFilter(filter.id, { field: value })}
              placeholder="字段"
              size="sm"
            />
          </div>

          {/* 操作符选择 */}
          <div className="w-[80px] shrink-0">
            <SearchableSelect
              options={OPERATOR_OPTIONS}
              value={filter.operator}
              onChange={(value) =>
                handleUpdateFilter(filter.id, { operator: value as FilterOperator })
              }
              placeholder="语法"
              size="sm"
            />
          </div>

          {/* 值输入 */}
          <div className="w-[200px] shrink-0">
            {operatorNeedsValue(filter.operator) ? (
              <Input
                type="text"
                value={filter.value || ''}
                onChange={(e) => handleUpdateFilter(filter.id, { value: e.target.value })}
                placeholder="值"
                className="h-8 text-sm"
              />
            ) : (
              <div className="flex h-8 items-center px-3 text-sm text-muted-foreground">
                -
              </div>
            )}
          </div>

          {/* 添加按钮 */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 shrink-0 text-muted-foreground hover:text-foreground"
            onClick={handleAddFilter}
            title="添加"
          >
            <Plus className="h-3.5 w-3.5" />
          </Button>

          {/* 删除按钮 */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
            onClick={() => handleRemoveFilter(filter.id)}
            title="删除"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      ))}

      {/* 空状态 - 添加第一个筛选条件 */}
      {filters.length === 0 && (
        <Button
          variant="outline"
          size="sm"
          onClick={handleAddFilter}
          className="w-full border-dashed"
        >
          <Plus className="mr-1.5 h-4 w-4" />
          添加筛选条件
        </Button>
      )}
    </div>
  )
}

export default FilterBuilder
