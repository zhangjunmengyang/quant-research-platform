/**
 * Log Explorer Page
 * 日志浏览器 - 支持字段筛选、JSON/表格视图切换
 *
 * 布局:
 * - 左侧边栏: 字段选择器 (控制显示哪些字段)
 * - 顶部: 搜索 + 筛选条件 (主题、级别、服务、时间范围)
 * - 主区域: JSON/表格/原始视图
 */

import { useState, useMemo, useEffect, useCallback } from 'react'
import {
  Search,
  Loader2,
  ChevronRight,
  Download,
  Copy,
  Check,
  ChevronLeft,
  GripVertical,
  Play,
  Save,
  Star,
  X,
} from 'lucide-react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useLogTopics, useLogQuery, useLogSQLQuery, FilterBuilder } from '@/features/log'
import type { LogEntry, LogQueryParams, LogFilterCondition } from '@/features/log'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'
import { cn } from '@/lib/utils'

// Display view type
type ViewType = 'json' | 'table' | 'raw'
type QueryMode = 'simple' | 'sql'

// SQL 模板接口
interface SQLTemplate {
  id: string
  name: string
  sql: string
  createdAt: string
}

// 从 localStorage 加载模板
function loadSQLTemplates(): SQLTemplate[] {
  try {
    const saved = localStorage.getItem('log_sql_templates')
    return saved ? JSON.parse(saved) : []
  } catch {
    return []
  }
}

// 保存模板到 localStorage
function saveSQLTemplates(templates: SQLTemplate[]) {
  localStorage.setItem('log_sql_templates', JSON.stringify(templates))
}

// 生成唯一 ID
function generateFilterId(): string {
  return `filter_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// Level badge colors
const levelBadgeColors: Record<string, string> = {
  debug: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  info: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
  error: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
}

// Time range quick options
const TIME_RANGE_OPTIONS: SelectOption[] = [
  { value: '', label: '全部' },
  { value: '1', label: '1小时' },
  { value: '6', label: '6小时' },
  { value: '24', label: '24小时' },
  { value: '168', label: '7天' },
]

// Format date to datetime-local input value (YYYY-MM-DDTHH:mm)
function formatDateTimeLocal(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

// Parse datetime-local input value to Date
function parseDateTimeLocal(value: string): Date | null {
  if (!value) return null
  const date = new Date(value)
  return isNaN(date.getTime()) ? null : date
}

// Topic category options (对应数据库中的 log_topics.name)
// 预定义主题: llm, mcp, system

// Field value getter
function getFieldValue(log: LogEntry, field: string): unknown {
  if (field.startsWith('data.')) {
    const dataKey = field.slice(5)
    return log.data[dataKey]
  }
  return (log as unknown as Record<string, unknown>)[field]
}

// Format timestamp to local timezone (UTC+8)
function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    // Format as YYYY-MM-DD HH:mm:ss in local timezone
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZone: 'Asia/Shanghai',
    }).replace(/\//g, '-')
  } catch {
    return timestamp
  }
}

// Format field value for display
function formatFieldValue(value: unknown, fieldName?: string): string {
  if (value === null || value === undefined) return ''
  // Format timestamp fields
  if (fieldName === 'timestamp' || fieldName?.includes('timestamp')) {
    return formatTimestamp(String(value))
  }
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

// Copy to clipboard
async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

// Sortable field item component
function SortableFieldItem({
  field,
  isSelected,
  onToggle,
  displayName,
}: {
  field: string
  isSelected: boolean
  onToggle: () => void
  displayName: string
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: field,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent',
        isDragging && 'bg-accent shadow-sm'
      )}
    >
      <input
        type="checkbox"
        checked={isSelected}
        onChange={onToggle}
        className="h-4 w-4 rounded border-input"
      />
      <div
        {...attributes}
        {...listeners}
        className="cursor-grab touch-none active:cursor-grabbing"
      >
        <GripVertical className="h-4 w-4 text-muted-foreground/50 hover:text-muted-foreground" />
      </div>
      <span className="truncate font-mono text-sm">{displayName}</span>
    </div>
  )
}

// Field selector sidebar with drag-and-drop support
// 分为"已选字段"和"可选字段"两个区域
function FieldSidebar({
  availableFields,
  selectedFields,
  fieldOrder,
  onToggleField,
  onReorderFields,
}: {
  availableFields: string[]
  selectedFields: Set<string>
  fieldOrder: string[]
  onToggleField: (field: string) => void
  onReorderFields: (newOrder: string[]) => void
}) {
  // 已选字段：按 fieldOrder 排序
  const selectedFieldsList = fieldOrder.filter((f) => selectedFields.has(f))
  // 新选中但不在 fieldOrder 中的字段追加到末尾
  const newSelectedFields = Array.from(selectedFields).filter((f) => !fieldOrder.includes(f))
  const orderedSelectedFields = [...selectedFieldsList, ...newSelectedFields]

  // 可选字段：未选中的字段，按 fieldOrder 排序（刚取消的在前面）
  const unselectedInOrder = fieldOrder.filter((f) => !selectedFields.has(f) && availableFields.includes(f))
  const unselectedNotInOrder = availableFields.filter((f) => !selectedFields.has(f) && !fieldOrder.includes(f))
  const unselectedFields = [...unselectedInOrder, ...unselectedNotInOrder]

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (over && active.id !== over.id) {
      const oldIndex = orderedSelectedFields.indexOf(active.id as string)
      const newIndex = orderedSelectedFields.indexOf(over.id as string)
      if (oldIndex !== -1 && newIndex !== -1) {
        const newOrder = arrayMove(orderedSelectedFields, oldIndex, newIndex)
        // 保留未选中字段的顺序，更新已选字段顺序
        onReorderFields([...newOrder, ...unselectedFields])
      }
    }
  }

  // 获取字段显示名称
  const getDisplayName = (field: string) => {
    return field.startsWith('data.') ? field.replace('data.', '') : field
  }

  return (
    <div className="flex w-60 flex-shrink-0 flex-col border-r bg-card">
      {/* Field list */}
      <div className="flex-1">
        {/* 已选字段 - 可拖动排序 */}
        <div className="border-b px-3 py-3">
          <div className="mb-2 text-xs font-medium text-muted-foreground">
            已选字段 <span className="text-muted-foreground/60">{orderedSelectedFields.length}</span>
          </div>
          {orderedSelectedFields.length > 0 ? (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext items={orderedSelectedFields} strategy={verticalListSortingStrategy}>
                <div className="space-y-1">
                  {orderedSelectedFields.map((field) => (
                    <SortableFieldItem
                      key={field}
                      field={field}
                      isSelected={true}
                      onToggle={() => onToggleField(field)}
                      displayName={getDisplayName(field)}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          ) : (
            <div className="py-2 text-xs text-muted-foreground">无已选字段</div>
          )}
        </div>

        {/* 可选字段 - 不可拖动 */}
        <div className="px-3 py-3">
          <div className="mb-2 text-xs font-medium text-muted-foreground">
            可选字段 <span className="text-muted-foreground/60">{unselectedFields.length}</span>
          </div>
          {unselectedFields.length > 0 ? (
            <div className="space-y-1">
              {unselectedFields.map((field) => (
                <label
                  key={field}
                  className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent"
                >
                  <input
                    type="checkbox"
                    checked={false}
                    onChange={() => onToggleField(field)}
                    className="h-4 w-4 rounded border-input cursor-pointer"
                  />
                  <span className="truncate font-mono text-sm">{getDisplayName(field)}</span>
                </label>
              ))}
            </div>
          ) : (
            <div className="py-2 text-xs text-muted-foreground">全部已选</div>
          )}
        </div>
      </div>
    </div>
  )
}

// JSON view for a single log
function LogJsonView({
  log,
  selectedFields,
  fieldOrder,
}: {
  log: LogEntry
  selectedFields: Set<string>
  fieldOrder: string[]
}) {
  const [copied, setCopied] = useState(false)

  const filteredLog = useMemo(() => {
    const result: Record<string, unknown> = {}
    // Use field order to maintain consistent ordering
    const orderedFields = fieldOrder.filter((f) => selectedFields.has(f))
    // Add any selected fields not in order
    const remainingFields = Array.from(selectedFields).filter((f) => !fieldOrder.includes(f))
    const allFields = [...orderedFields, ...remainingFields]

    allFields.forEach((field) => {
      const value = getFieldValue(log, field)
      const displayKey = field.startsWith('data.') ? field.slice(5) : field
      // Format timestamp fields to local timezone
      if (field === 'timestamp' || field.includes('timestamp')) {
        result[displayKey] = value ? formatTimestamp(String(value)) : null
      } else {
        // 即使值为空也显示，保证所见即所得
        result[displayKey] = value ?? null
      }
    })
    return result
  }, [log, selectedFields, fieldOrder])

  const jsonString = JSON.stringify(filteredLog, null, 2)

  const handleCopy = async () => {
    const success = await copyToClipboard(jsonString)
    if (success) {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="group relative rounded-lg border bg-card p-4">
      <button
        onClick={handleCopy}
        className="absolute right-3 top-3 rounded-md p-1.5 opacity-0 transition-opacity hover:bg-accent group-hover:opacity-100"
        title="复制"
      >
        {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4 text-muted-foreground" />}
      </button>
      <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-sm">{jsonString}</pre>
    </div>
  )
}

// Raw view for a single log
function LogRawView({ log }: { log: LogEntry }) {
  const [copied, setCopied] = useState(false)

  const formattedTime = formatTimestamp(log.timestamp)
  const rawString = `[${formattedTime}] [${log.level.toUpperCase()}] [${log.service}] ${log.message}`

  const handleCopy = async () => {
    const success = await copyToClipboard(rawString)
    if (success) {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="group relative rounded-lg border bg-card p-4">
      <button
        onClick={handleCopy}
        className="absolute right-3 top-3 rounded-md p-1.5 opacity-0 transition-opacity hover:bg-accent group-hover:opacity-100"
        title="复制"
      >
        {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4 text-muted-foreground" />}
      </button>
      <div className="font-mono text-sm">
        <span className="text-muted-foreground">{formattedTime}</span>{' '}
        <span className={cn('rounded px-1.5 py-0.5', levelBadgeColors[log.level.toLowerCase()])}>
          {log.level.toUpperCase()}
        </span>{' '}
        <span className="text-blue-500">[{log.service}]</span> {log.message}
        {Object.keys(log.data).length > 0 && (
          <div className="mt-2 text-muted-foreground">{JSON.stringify(log.data, null, 2)}</div>
        )}
      </div>
    </div>
  )
}

// Table view
function TableView({
  logs,
  selectedFields,
  fieldOrder,
  sortField,
  sortOrder,
  onSort,
  expandedRows,
  onToggleRow,
}: {
  logs: LogEntry[]
  selectedFields: Set<string>
  fieldOrder: string[]
  sortField: string | null
  sortOrder: 'asc' | 'desc'
  onSort: (field: string) => void
  expandedRows: Set<number>
  onToggleRow: (id: number) => void
}) {
  // Use field order to maintain consistent ordering
  const orderedFields = fieldOrder.filter((f) => selectedFields.has(f))
  const remainingFields = Array.from(selectedFields).filter((f) => !fieldOrder.includes(f))
  const fields = [...orderedFields, ...remainingFields]

  return (
    <div className="overflow-x-auto">
      {/* Header */}
      <div className="sticky top-0 z-10 flex border-b bg-muted/50">
        {fields.map((field) => (
          <div
            key={field}
            className="flex min-w-[120px] flex-1 cursor-pointer items-center gap-1 px-4 py-3 text-sm font-medium hover:bg-muted"
            onClick={() => onSort(field)}
          >
            <span className="truncate">{field.replace('data.', '')}</span>
            {sortField === field && (
              <span className="text-primary">{sortOrder === 'asc' ? '↑' : '↓'}</span>
            )}
          </div>
        ))}
      </div>

      {/* Rows */}
      {logs.map((log) => (
        <div key={log.id} className="border-b hover:bg-muted/30">
          <div className="flex cursor-pointer" onClick={() => onToggleRow(log.id)}>
            {fields.map((field) => {
              const value = getFieldValue(log, field)
              const displayValue = formatFieldValue(value, field)

              return (
                <div
                  key={field}
                  className="min-w-[120px] flex-1 truncate px-4 py-3 font-mono text-sm"
                  title={displayValue}
                >
                  {field === 'level' ? (
                    <span
                      className={cn(
                        'rounded px-1.5 py-0.5',
                        levelBadgeColors[String(value).toLowerCase()] || ''
                      )}
                    >
                      {displayValue}
                    </span>
                  ) : field === 'trace_id' && displayValue ? (
                    <span className="text-amber-600">{displayValue}</span>
                  ) : field === 'data.workflow' ? (
                    <span className={cn(
                      'rounded px-1.5 py-0.5 text-xs',
                      displayValue === 'fill' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                      displayValue === 'review' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300' :
                      'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                    )}>
                      {displayValue}
                    </span>
                  ) : field === 'data.status' ? (
                    <span className={cn(
                      'rounded px-1.5 py-0.5 text-xs',
                      displayValue === 'success' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                      displayValue === 'failed' ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' :
                      'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                    )}>
                      {displayValue}
                    </span>
                  ) : field === 'data.method' ? (
                    <span className={cn(
                      'rounded px-1.5 py-0.5 text-xs font-mono',
                      displayValue === 'tools/call' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' :
                      displayValue === 'resources/read' ? 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300' :
                      displayValue === 'initialize' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                      'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                    )}>
                      {displayValue}
                    </span>
                  ) : field === 'data.tool_name' ? (
                    <span className="text-indigo-600 dark:text-indigo-400 font-mono">{displayValue}</span>
                  ) : field === 'data.server_name' ? (
                    <span className="text-purple-600 dark:text-purple-400">{displayValue}</span>
                  ) : field === 'data.server_port' ? (
                    <span className="text-orange-600 dark:text-orange-400 font-mono">{displayValue}</span>
                  ) : field === 'data.tool_arguments' || field === 'data.response_data' ? (
                    <span className="text-gray-600 dark:text-gray-400 font-mono text-xs">
                      {displayValue.length > 50 ? displayValue.slice(0, 50) + '...' : displayValue}
                    </span>
                  ) : field === 'data.error_message' && displayValue ? (
                    <span className="text-red-600 dark:text-red-400">{displayValue}</span>
                  ) : field === 'data.factor_name' || field === 'data.field' ? (
                    <span className="text-blue-600 dark:text-blue-400">{displayValue}</span>
                  ) : (
                    displayValue || <span className="text-muted-foreground">-</span>
                  )}
                </div>
              )
            })}
          </div>
          {expandedRows.has(log.id) && (
            <div className="border-t bg-muted/20 p-4">
              <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-sm">
                {JSON.stringify({ ...log, data: log.data }, null, 2)}
              </pre>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// Default field order - prioritize task context for LLM and MCP logs
const DEFAULT_FIELD_ORDER = [
  'timestamp', 'level', 'service', 'message', 'topic', 'logger', 'trace_id',
  // MCP log fields (prioritized for debugging)
  'data.server_name', 'data.server_port', 'data.method', 'data.tool_name',
  'data.tool_arguments', 'data.status', 'data.duration_ms',
  'data.response_summary', 'data.response_data', 'data.error_message',
  // LLM log task context fields
  'data.workflow', 'data.factor_name', 'data.field',
  'data.model', 'data.total_tokens', 'data.cost',
  // LLM log content fields
  'data.system_prompt', 'data.user_prompt', 'data.response_content',
]
// Default selected fields - basic fields + MCP/LLM task context
const DEFAULT_SELECTED_FIELDS = new Set([
  'timestamp', 'level', 'service', 'message',
  // MCP fields (auto-selected for debugging)
  'data.server_name', 'data.server_port', 'data.tool_name',
  'data.tool_arguments', 'data.status', 'data.duration_ms',
  'data.response_data', 'data.error_message',
  // LLM task context (auto-selected when available)
  'data.workflow', 'data.factor_name', 'data.field',
  'data.total_tokens',
])

// Main component
export function Component() {
  // State
  const [mode, setMode] = useState<QueryMode>('simple')
  const [viewType, setViewType] = useState<ViewType>('json')
  const [selectedFields, setSelectedFields] = useState<Set<string>>(new Set(DEFAULT_SELECTED_FIELDS))
  const [fieldOrder, setFieldOrder] = useState<string[]>(DEFAULT_FIELD_ORDER)
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())
  const [sortField, setSortField] = useState<string | null>('timestamp')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [timeRange, setTimeRange] = useState('1') // 默认 1 小时
  const [sqlQuery, setSqlQuery] = useState(
    'SELECT * FROM logs l JOIN log_topics t ON l.topic_id = t.id ORDER BY l.timestamp DESC LIMIT 100'
  )

  // 高级筛选条件 - 默认有一个空筛选条件
  const [advancedFilters, setAdvancedFilters] = useState<LogFilterCondition[]>([
    { id: generateFilterId(), field: '', operator: '=', value: '' }
  ])

  // SQL 模板状态
  const [sqlTemplates, setSqlTemplates] = useState<SQLTemplate[]>(() => loadSQLTemplates())
  const [showTemplates, setShowTemplates] = useState(false)
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [templateName, setTemplateName] = useState('')

  // Query params - 默认设置时间范围为最近 1 小时
  const [queryParams, setQueryParams] = useState<LogQueryParams>(() => {
    const now = new Date()
    const start = new Date(now.getTime() - 1 * 60 * 60 * 1000) // 1 小时前
    return {
      page: 1,
      page_size: 50,
      start_time: start.toISOString(),
      end_time: now.toISOString(),
    }
  })

  // Hooks
  const { data: topics } = useLogTopics()
  const { data: queryResult, isLoading: queryLoading } = useLogQuery(queryParams, mode === 'simple')
  const sqlMutation = useLogSQLQuery()

  // Build topic options
  const topicOptions: SelectOption[] = useMemo(
    () => topics?.map((t) => ({ value: t.name, label: t.display_name })) || [],
    [topics]
  )

  // Current logs based on mode
  const currentLogs = mode === 'simple' ? queryResult?.logs : sqlMutation.data?.logs
  const total = mode === 'simple' ? queryResult?.total : sqlMutation.data?.total
  const isLoading = mode === 'simple' ? queryLoading : sqlMutation.isPending

  // Available fields based on selected topic's field_schema
  const availableFields = useMemo(() => {
    // 基础字段始终可用
    const baseFields = ['timestamp', 'topic', 'level', 'service', 'logger', 'trace_id', 'message']

    if (!topics || topics.length === 0) {
      return baseFields
    }

    // 根据选中的主题获取扩展字段
    let dataFields: string[] = []
    const selectedTopic = queryParams.topic

    if (selectedTopic) {
      // 选中了特定主题，使用该主题的 field_schema
      const topic = topics.find((t) => t.name === selectedTopic)
      if (topic?.field_schema) {
        // field_schema 是 JSON Schema 格式，有 properties 字段
        const schema = topic.field_schema as { properties?: Record<string, unknown> }
        if (schema.properties) {
          dataFields = Object.keys(schema.properties).map((f) => `data.${f}`)
        }
      }
    }

    return [...baseFields, ...dataFields.sort()]
  }, [topics, queryParams.topic])

  // Auto-select first topic when topics are loaded and no topic is selected
  useEffect(() => {
    if (topics && topics.length > 0 && !queryParams.topic && topics[0]) {
      setQueryParams((prev) => ({ ...prev, topic: topics[0]!.name }))
    }
  }, [topics, queryParams.topic])

  // Update selected fields when available fields change
  useEffect(() => {
    if (availableFields.length > 0) {
      setSelectedFields((prev) => {
        const next = new Set<string>()
        const availableSet = new Set(availableFields)

        // 保留在 availableFields 中的已选字段
        prev.forEach((field) => {
          if (availableSet.has(field)) {
            next.add(field)
          }
        })

        // 自动选中新增的 data.* 字段
        availableFields.forEach((field) => {
          if (field.startsWith('data.') && !prev.has(field)) {
            next.add(field)
          }
        })

        return next
      })
    }
  }, [availableFields])

  // Sort logs
  const sortedLogs = useMemo(() => {
    if (!currentLogs || !sortField) return currentLogs || []

    return [...currentLogs].sort((a, b) => {
      const aVal = getFieldValue(a, sortField)
      const bVal = getFieldValue(b, sortField)

      if (aVal === bVal) return 0
      if (aVal === null || aVal === undefined) return 1
      if (bVal === null || bVal === undefined) return -1

      const comparison = String(aVal).localeCompare(String(bVal))
      return sortOrder === 'asc' ? comparison : -comparison
    })
  }, [currentLogs, sortField, sortOrder])

  // Handlers - 执行查询
  const handleQuery = useCallback(() => {
    // 将高级筛选条件合并到 queryParams
    setQueryParams((prev) => ({
      ...prev,
      advanced_filters: advancedFilters.filter((f) => f.field), // 过滤掉空字段
      page: 1,
    }))
  }, [advancedFilters])

  const handleExecuteSQL = () => {
    sqlMutation.mutate({ sql: sqlQuery, page: 1, page_size: 100 })
  }

  const handleTimeRangeChange = (value: string) => {
    setTimeRange(value)
    const hours = parseInt(value)
    if (hours) {
      const now = new Date()
      const start = new Date(now.getTime() - hours * 60 * 60 * 1000)
      setQueryParams({
        ...queryParams,
        start_time: start.toISOString(),
        end_time: now.toISOString(),
        page: 1,
      })
    } else {
      setQueryParams({
        ...queryParams,
        start_time: undefined,
        end_time: undefined,
        page: 1,
      })
    }
  }

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
  }

  const handleToggleField = (field: string) => {
    setSelectedFields((prev) => {
      const next = new Set(prev)
      const wasSelected = next.has(field)
      if (wasSelected) {
        next.delete(field)
        // 取消选中：将字段移到 fieldOrder 开头（可选列表第一个）
        setFieldOrder((prevOrder) => {
          const filtered = prevOrder.filter((f) => f !== field)
          return [field, ...filtered]
        })
      } else {
        next.add(field)
        // 新选中：将字段移到 fieldOrder 末尾（已选列表最后一个）
        setFieldOrder((prevOrder) => {
          const filtered = prevOrder.filter((f) => f !== field)
          return [...filtered, field]
        })
      }
      return next
    })
  }

  const handleReorderFields = useCallback((newOrder: string[]) => {
    setFieldOrder(newOrder)
  }, [])

  const toggleRow = (id: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleDownload = () => {
    if (!currentLogs) return

    const content = currentLogs.map((log) => JSON.stringify(log)).join('\n')

    const blob = new Blob([content], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `logs-${new Date().toISOString().slice(0, 10)}.jsonl`
    a.click()
    URL.revokeObjectURL(url)
  }

  // SQL 模板功能
  const handleSaveTemplate = () => {
    if (!templateName.trim()) return

    const newTemplate: SQLTemplate = {
      id: `tpl_${Date.now()}`,
      name: templateName.trim(),
      sql: sqlQuery,
      createdAt: new Date().toISOString(),
    }

    const updated = [...sqlTemplates, newTemplate]
    setSqlTemplates(updated)
    saveSQLTemplates(updated)
    setTemplateName('')
    setShowSaveDialog(false)
  }

  const handleDeleteTemplate = (id: string) => {
    const updated = sqlTemplates.filter((t) => t.id !== id)
    setSqlTemplates(updated)
    saveSQLTemplates(updated)
  }

  const handleApplyTemplate = (template: SQLTemplate) => {
    setSqlQuery(template.sql)
    setShowTemplates(false)
  }

  const logs = sortedLogs

  const currentPage = queryParams.page ?? 1

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col">
      {/* Top search and filter area */}
      <div className="border-b bg-card">
        {/* Row 1: Topic + Time range + Limit + Query button (fixed) */}
        <div className="flex items-center gap-3 border-b px-4 py-2.5">
          {/* Topic selector */}
          <div className="w-[140px] shrink-0">
            <SearchableSelect
              options={topicOptions}
              value={queryParams.topic || ''}
              onChange={(value) => setQueryParams({ ...queryParams, topic: value || undefined, page: 1 })}
              placeholder="主题"
              searchPlaceholder="搜索..."
              size="sm"
            />
          </div>

          {/* Time range quick selector */}
          <div className="w-[90px] shrink-0">
            <SearchableSelect
              options={TIME_RANGE_OPTIONS}
              value={timeRange}
              onChange={handleTimeRangeChange}
              placeholder="时间"
              size="sm"
            />
          </div>

          {/* Start time picker */}
          <Input
            type="datetime-local"
            value={queryParams.start_time ? formatDateTimeLocal(new Date(queryParams.start_time)) : ''}
            onChange={(e) => {
              const date = parseDateTimeLocal(e.target.value)
              setTimeRange('') // Clear quick select
              setQueryParams({
                ...queryParams,
                start_time: date?.toISOString(),
                page: 1,
              })
            }}
            className="h-8 w-[180px] text-sm"
          />
          <span className="text-muted-foreground text-sm">-</span>
          {/* End time picker */}
          <Input
            type="datetime-local"
            value={queryParams.end_time ? formatDateTimeLocal(new Date(queryParams.end_time)) : ''}
            onChange={(e) => {
              const date = parseDateTimeLocal(e.target.value)
              setTimeRange('') // Clear quick select
              setQueryParams({
                ...queryParams,
                end_time: date?.toISOString(),
                page: 1,
              })
            }}
            className="h-8 w-[180px] text-sm"
          />

          <div className="flex-1" />

          {/* Limit input */}
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="text-sm text-muted-foreground">limit</span>
            <Input
              type="number"
              min={1}
              max={10000}
              value={queryParams.page_size || 50}
              onChange={(e) => {
                const val = parseInt(e.target.value) || 50
                setQueryParams({ ...queryParams, page_size: Math.min(Math.max(val, 1), 10000), page: 1 })
              }}
              className="h-8 w-[70px] text-sm"
            />
          </div>

          {/* Query button - fixed position */}
          <Button onClick={handleQuery} size="sm" className="h-8 shrink-0">
            <Search className="mr-1.5 h-4 w-4" />
            查询
          </Button>

          {/* Mode toggle */}
          <div className="flex rounded-md border shrink-0">
            <Button
              variant={mode === 'simple' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setMode('simple')}
              className="rounded-r-none h-8 text-xs px-3"
            >
              简单
            </Button>
            <Button
              variant={mode === 'sql' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setMode('sql')}
              className="rounded-l-none h-8 text-xs px-3"
            >
              SQL
            </Button>
          </div>
        </div>

        {/* Row 2: Filters or SQL editor */}
        {mode === 'simple' ? (
          <div className="px-4 py-2.5">
            {/* 筛选区域 - 整体边框 */}
            <div className="rounded-md border bg-muted/20 px-3 py-2">
              <FilterBuilder
                filters={advancedFilters}
                onChange={setAdvancedFilters}
                availableFields={availableFields}
              />
            </div>
          </div>
        ) : (
          <div className="px-4 py-3">
            {/* SQL editor header with template buttons */}
            <div className="mb-2 flex items-center justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowSaveDialog(true)}
                className="h-7 text-xs"
                title="保存为模板"
              >
                <Save className="mr-1 h-3.5 w-3.5" />
                保存
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowTemplates(!showTemplates)}
                className={cn("h-7 text-xs", showTemplates && "bg-accent")}
                title="收藏的模板"
              >
                <Star className="mr-1 h-3.5 w-3.5" />
                收藏
              </Button>
            </div>

            {/* 模板列表 */}
            {showTemplates && (
              <div className="mb-3 rounded-md border bg-muted/30 p-3">
                <div className="text-xs font-medium text-muted-foreground mb-2">收藏的模板</div>
                {sqlTemplates.length === 0 ? (
                  <div className="text-xs text-muted-foreground py-2">暂无保存的模板</div>
                ) : (
                  <div className="space-y-2 max-h-[200px] overflow-y-auto">
                    {sqlTemplates.map((tpl) => (
                      <div
                        key={tpl.id}
                        className="flex items-center gap-2 rounded-md bg-background p-2 hover:bg-accent cursor-pointer"
                        onClick={() => handleApplyTemplate(tpl)}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate">{tpl.name}</div>
                          <div className="text-xs text-muted-foreground truncate font-mono">{tpl.sql}</div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 shrink-0"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteTemplate(tpl.id)
                          }}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 保存模板对话框 */}
            {showSaveDialog && (
              <div className="mb-3 rounded-md border bg-muted/30 p-3">
                <div className="text-xs font-medium text-muted-foreground mb-2">保存为模板</div>
                <div className="flex gap-2">
                  <Input
                    type="text"
                    placeholder="模板名称"
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    className="h-8 text-sm"
                    onKeyDown={(e) => e.key === 'Enter' && handleSaveTemplate()}
                  />
                  <Button size="sm" onClick={handleSaveTemplate} className="h-8">
                    保存
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setShowSaveDialog(false)
                      setTemplateName('')
                    }}
                    className="h-8"
                  >
                    取消
                  </Button>
                </div>
              </div>
            )}

            {/* SQL editor */}
            <div className="flex gap-3">
              <div className="flex-1">
                <textarea
                  value={sqlQuery}
                  onChange={(e) => setSqlQuery(e.target.value)}
                  placeholder="SELECT * FROM logs l JOIN log_topics t ON l.topic_id = t.id WHERE ... ORDER BY l.timestamp DESC LIMIT 100"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring min-h-[80px] resize-y"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                      handleExecuteSQL()
                    }
                  }}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Button onClick={handleExecuteSQL} disabled={sqlMutation.isPending} className="h-9">
                  <Play className="mr-1.5 h-4 w-4" />
                  执行
                </Button>
                <span className="text-xs text-muted-foreground">Ctrl+Enter</span>
              </div>
            </div>
            {sqlMutation.isError && (
              <div className="mt-2 text-sm text-destructive">
                查询错误: {sqlMutation.error?.message || '未知错误'}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Main area: Sidebar + Content */}
      <div className="flex flex-1">
        {/* Left sidebar: Field selector */}
        <FieldSidebar
          availableFields={availableFields}
          selectedFields={selectedFields}
          fieldOrder={fieldOrder}
          onToggleField={handleToggleField}
          onReorderFields={handleReorderFields}
        />

        {/* Content area */}
        <div className="flex flex-1 flex-col">
          {/* Content toolbar */}
          <div className="flex items-center gap-3 border-b bg-card px-4 py-2">
            {/* View type toggle */}
            <div className="flex rounded-md border">
              <Button
                variant={viewType === 'raw' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewType('raw')}
                className="rounded-r-none h-8"
              >
                原始
              </Button>
              <Button
                variant={viewType === 'json' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewType('json')}
                className="rounded-none border-x h-8"
              >
                json
              </Button>
              <Button
                variant={viewType === 'table' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewType('table')}
                className="rounded-l-none h-8"
              >
                kv
              </Button>
            </div>

            {/* Download */}
            <Button variant="ghost" size="sm" onClick={handleDownload} disabled={!logs.length} className="h-8">
              <Download className="mr-1.5 h-4 w-4" />
              下载
            </Button>

            {/* Info text */}
            <span className="text-sm text-muted-foreground">最多展示和下载10,000行数据</span>

            <div className="flex-1" />

            {/* Page size selector */}
            <div className="w-[100px]">
              <SearchableSelect
                options={[
                  { value: '20', label: '20条/页' },
                  { value: '50', label: '50条/页' },
                  { value: '100', label: '100条/页' },
                  { value: '200', label: '200条/页' },
                ]}
                value={String(queryParams.page_size || 50)}
                onChange={(value) => setQueryParams({ ...queryParams, page_size: parseInt(value) || 50, page: 1 })}
                size="sm"
              />
            </div>

            {/* Pagination */}
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setQueryParams({ ...queryParams, page: currentPage - 1 })}
                disabled={currentPage <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="min-w-[40px] text-center text-sm">{currentPage}</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setQueryParams({ ...queryParams, page: currentPage + 1 })}
                disabled={!queryResult?.has_more}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            {/* Total count */}
            <span className="text-sm text-muted-foreground">共 {total ?? 0} 条</span>
          </div>

        {/* Log content */}
        <div className="bg-muted/30 p-4">
          {isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : !logs.length ? (
            <div className="flex h-64 flex-col items-center justify-center text-muted-foreground">
              <Search className="h-12 w-12 opacity-50" />
              <p className="mt-4 text-sm">没有找到日志</p>
            </div>
          ) : viewType === 'json' ? (
            <div className="space-y-3">
              {logs.map((log) => (
                <LogJsonView key={log.id} log={log} selectedFields={selectedFields} fieldOrder={fieldOrder} />
              ))}
            </div>
          ) : viewType === 'raw' ? (
            <div className="space-y-3">
              {logs.map((log) => (
                <LogRawView key={log.id} log={log} />
              ))}
            </div>
          ) : (
            <div className="rounded-lg border bg-card">
              <TableView
                logs={logs}
                selectedFields={selectedFields}
                fieldOrder={fieldOrder}
                sortField={sortField}
                sortOrder={sortOrder}
                onSort={handleSort}
                expandedRows={expandedRows}
                onToggleRow={toggleRow}
              />
            </div>
          )}
        </div>

          {/* Bottom pagination bar */}
          {logs.length > 0 && (
            <div className="flex items-center justify-end gap-3 border-t bg-card px-4 py-2">
              {/* Page size selector */}
              <div className="w-[100px]">
                <SearchableSelect
                  options={[
                    { value: '20', label: '20条/页' },
                    { value: '50', label: '50条/页' },
                    { value: '100', label: '100条/页' },
                    { value: '200', label: '200条/页' },
                  ]}
                  value={String(queryParams.page_size || 50)}
                  onChange={(value) => setQueryParams({ ...queryParams, page_size: parseInt(value) || 50, page: 1 })}
                  size="sm"
                />
              </div>

              {/* Pagination */}
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setQueryParams({ ...queryParams, page: currentPage - 1 })}
                  disabled={currentPage <= 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="min-w-[40px] text-center text-sm">{currentPage}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setQueryParams({ ...queryParams, page: currentPage + 1 })}
                  disabled={!queryResult?.has_more}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>

              {/* Total count */}
              <span className="text-sm text-muted-foreground">共 {total ?? 0} 条</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
