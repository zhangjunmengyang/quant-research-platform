/**
 * Factor Pipeline Page
 * LLM 数据清洗 Pipeline 管理页面
 * 按任务拆分为多个 Tab: 概览、因子入库、字段填充、质量审核
 */

import React, { useState, useRef, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  Check,
  CheckCircle2,
  ClipboardCheck,
  Copy,
  Download,
  FileSearch,
  FolderInput,
  Loader2,
  PenLine,
  Play,
  RefreshCw,
  Settings,
  Sparkles,
  Square,
  X,
  XCircle,
  Zap,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  pipelineApi,
  type FillableField,
  type FillMode,
  type PipelineStatus,
  type FillRequest,
  type ReviewRequest,
  type PromptConfig,
  type PromptConfigUpdate,
  type PromptVariable,
  type LLMModelInfo,
  type FillLog,
  type FillProgress,
} from '@/features/factor/pipeline-api'
import { useFillProgress } from '@/features/factor/hooks'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'
import { toast } from '@/components/ui/toast'

// ==================== Types ====================

type TabType = 'ingest' | 'fill' | 'review' | 'prompts'

// ==================== Constants ====================

const FILL_MODE_OPTIONS: SelectOption[] = [
  { value: 'incremental', label: '增量 (仅填充空值)' },
  { value: 'full', label: '全量 (重新填充所有)' },
]

const FIELD_LABELS: Record<string, string> = {
  style: '风格分类',
  tags: '因子标签',
  formula: '计算公式',
  input_data: '输入数据',
  value_range: '值域范围',
  description: '因子描述',
  analysis: '因子分析',
  llm_score: 'LLM评分',
}

// 字段填充顺序（与后端保持一致）
const FIELD_ORDER = ['style', 'formula', 'input_data', 'value_range', 'tags', 'description', 'analysis', 'llm_score']

const REVIEW_PROMPT = {
  system: `你是一个量化因子代码审核专家。请对因子进行反思审核。

对于因子 {{filename}}，请检查：
1. 代码逻辑是否与公式描述一致
2. 输入数据字段是否正确（应使用: o,h,l,c,v,qv,tn,bv,bqv）
3. 值域是否合理
4. 是否存在致命陷阱（分母为零、未来函数、符号问题等）
5. 因子元信息描述是否准确
6. 标签是否准确反映因子特征（计算特征、信号特征、数据来源、复杂度、适用场景）

请返回 JSON 格式的审核结果。`,
}

// ==================== Ingest Tab ====================

function IngestTab() {
  const queryClient = useQueryClient()
  const [selectedFactors, setSelectedFactors] = useState<string[]>([])

  const {
    data: discoverResult,
    isLoading: discoverLoading,
    refetch: refetchDiscover,
  } = useQuery({
    queryKey: ['pipeline-discover'],
    queryFn: pipelineApi.discover,
    enabled: false,
  })

  const ingestMutation = useMutation({
    mutationFn: (factors: string[]) =>
      pipelineApi.ingest({ factors, fill_fields: true }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-status'] })
      queryClient.invalidateQueries({ queryKey: ['pipeline-discover'] })
      queryClient.invalidateQueries({ queryKey: ['factors'] })
      setSelectedFactors([])
      toast.success('入库成功', `已入库 ${result.ingested} 个因子`)
    },
    onError: (error) => {
      toast.error('入库失败', (error as Error).message)
    },
  })

  const handleSelectAll = () => {
    if (discoverResult?.pending) {
      if (selectedFactors.length === discoverResult.pending.length) {
        setSelectedFactors([])
      } else {
        setSelectedFactors([...discoverResult.pending])
      }
    }
  }

  const handleToggle = (factor: string) => {
    setSelectedFactors((prev) =>
      prev.includes(factor) ? prev.filter((f) => f !== factor) : [...prev, factor]
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileSearch className="h-5 w-5 text-primary" />
          <div>
            <h3 className="font-semibold">因子发现与入库</h3>
            <p className="text-sm text-muted-foreground">扫描因子目录，发现并入库新因子</p>
          </div>
        </div>
        <button
          onClick={() => refetchDiscover()}
          disabled={discoverLoading}
          className="flex items-center gap-2 rounded-md border px-4 py-2 text-sm hover:bg-accent disabled:opacity-50"
        >
          <RefreshCw className={cn('h-4 w-4', discoverLoading && 'animate-spin')} />
          扫描目录
        </button>
      </div>

      {/* Content */}
      <div className="rounded-lg border bg-card">
        <div className="p-6">
          {discoverLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : discoverResult ? (
            <div className="space-y-6">
              {/* Summary */}
              <div className="grid grid-cols-5 gap-4">
                <div className="text-center p-4 rounded-lg bg-muted/50">
                  <p className="text-2xl font-semibold">{discoverResult.cataloged.length}</p>
                  <p className="text-sm text-muted-foreground">已入库</p>
                </div>
                <div className="text-center p-4 rounded-lg bg-yellow-50 dark:bg-yellow-900/20">
                  <p className="text-2xl font-semibold text-yellow-600">
                    {discoverResult.pending.length}
                  </p>
                  <p className="text-sm text-muted-foreground">待入库</p>
                  {discoverResult.pending.length > 0 && (
                    <p className="text-xs text-muted-foreground mt-1">
                      时序 {discoverResult.pending_time_series?.length || 0} / 截面 {discoverResult.pending_cross_section?.length || 0}
                    </p>
                  )}
                </div>
                <div className="text-center p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20">
                  <p className="text-2xl font-semibold text-blue-600">
                    {discoverResult.pending_time_series?.length || 0}
                  </p>
                  <p className="text-sm text-muted-foreground">待入库时序</p>
                </div>
                <div className="text-center p-4 rounded-lg bg-purple-50 dark:bg-purple-900/20">
                  <p className="text-2xl font-semibold text-purple-600">
                    {discoverResult.pending_cross_section?.length || 0}
                  </p>
                  <p className="text-sm text-muted-foreground">待入库截面</p>
                </div>
                <div className="text-center p-4 rounded-lg bg-red-50 dark:bg-red-900/20">
                  <p className="text-2xl font-semibold text-red-600">
                    {discoverResult.missing_files.length}
                  </p>
                  <p className="text-sm text-muted-foreground">文件缺失</p>
                </div>
              </div>

              {/* Pending factors list */}
              {discoverResult.pending.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-medium">待入库因子</h4>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={handleSelectAll}
                        className="text-sm text-primary hover:underline"
                      >
                        {selectedFactors.length === discoverResult.pending.length
                          ? '取消全选'
                          : '全选'}
                      </button>
                      <button
                        onClick={() => ingestMutation.mutate(selectedFactors)}
                        disabled={selectedFactors.length === 0 || ingestMutation.isPending}
                        className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                      >
                        {ingestMutation.isPending ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Download className="h-4 w-4" />
                        )}
                        入库 ({selectedFactors.length})
                      </button>
                    </div>
                  </div>
                  <div className="max-h-64 overflow-auto rounded-lg border">
                    {discoverResult.pending.map((factor) => {
                      const isTimeSeries = discoverResult.pending_time_series?.includes(factor)
                      const isCrossSection = discoverResult.pending_cross_section?.includes(factor)
                      return (
                        <label
                          key={factor}
                          className="flex items-center gap-3 px-4 py-3 hover:bg-muted/50 cursor-pointer border-b last:border-b-0"
                        >
                          <input
                            type="checkbox"
                            checked={selectedFactors.includes(factor)}
                            onChange={() => handleToggle(factor)}
                            className="rounded border-gray-300"
                          />
                          <span className="text-sm font-mono flex-1">{factor}</span>
                          <span
                            className={cn(
                              'text-xs px-2 py-0.5 rounded-full',
                              isTimeSeries
                                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                                : isCrossSection
                                ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                                : 'bg-gray-100 text-gray-600'
                            )}
                          >
                            {isTimeSeries ? '时序' : isCrossSection ? '截面' : '未知'}
                          </span>
                        </label>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Missing files warning */}
              {discoverResult.missing_files.length > 0 && (
                <div className="rounded-lg bg-red-50 dark:bg-red-900/20 p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-medium text-red-600">文件缺失警告</h4>
                      <p className="text-sm text-red-600/80 mt-1">
                        以下因子在数据库中存在但源文件已丢失：
                      </p>
                      <ul className="text-sm text-red-600/80 mt-2 list-disc list-inside">
                        {discoverResult.missing_files.slice(0, 5).map((f) => (
                          <li key={f}>{f}</li>
                        ))}
                        {discoverResult.missing_files.length > 5 && (
                          <li>... 等 {discoverResult.missing_files.length - 5} 个</li>
                        )}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              点击"扫描目录"按钮发现新因子
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ==================== Variable Autocomplete Textarea ====================

function VariableTextarea({
  value,
  onChange,
  placeholder,
  minRows = 3,
  className,
  variables = [],
}: {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  minRows?: number
  className?: string
  variables?: PromptVariable[]
}) {
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [suggestionIndex, setSuggestionIndex] = useState(0)
  const [cursorPosition, setCursorPosition] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // 自适应高度
  const adjustHeight = () => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${textarea.scrollHeight}px`
    }
  }

  React.useEffect(() => {
    adjustHeight()
  }, [value])

  // 检测是否正在输入变量
  const getVariableContext = (text: string, pos: number) => {
    const beforeCursor = text.slice(0, pos)
    const match = beforeCursor.match(/\{\{(\w*)$/)
    if (match) {
      return { prefix: match[1], start: match.index! }
    }
    return null
  }

  const context = getVariableContext(value, cursorPosition)
  const filteredVars = context
    ? variables.filter(v =>
        v.name.toLowerCase().startsWith((context.prefix ?? '').toLowerCase())
      )
    : []

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!showSuggestions || filteredVars.length === 0) return

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSuggestionIndex(i => (i + 1) % filteredVars.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSuggestionIndex(i => (i - 1 + filteredVars.length) % filteredVars.length)
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      const selectedVar = filteredVars[suggestionIndex]
      if (showSuggestions && selectedVar) {
        e.preventDefault()
        insertVariable(selectedVar.name)
      }
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
    }
  }

  const insertVariable = (varName: string) => {
    if (!context || !textareaRef.current) return

    const before = value.slice(0, context.start)
    const after = value.slice(cursorPosition)
    const newValue = `${before}{{${varName}}}${after}`
    onChange(newValue)

    // 移动光标到变量后
    const newPos = context.start + varName.length + 4
    setTimeout(() => {
      textareaRef.current?.setSelectionRange(newPos, newPos)
      textareaRef.current?.focus()
    }, 0)

    setShowSuggestions(false)
  }

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value
    const newPos = e.target.selectionStart || 0
    onChange(newValue)
    setCursorPosition(newPos)

    const ctx = getVariableContext(newValue, newPos)
    setShowSuggestions(!!ctx)
    setSuggestionIndex(0)
  }

  const handleSelect = (e: React.SyntheticEvent<HTMLTextAreaElement>) => {
    const target = e.target as HTMLTextAreaElement
    setCursorPosition(target.selectionStart || 0)
  }

  const minHeight = minRows * 24 // 约 24px 每行

  return (
    <div className="relative">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onSelect={handleSelect}
        onKeyDown={handleKeyDown}
        onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
        placeholder={placeholder}
        style={{ minHeight: `${minHeight}px` }}
        className={cn(
          'w-full rounded-md border bg-muted/50 p-3 font-mono text-sm resize-none overflow-hidden focus:outline-none focus:ring-2 focus:ring-primary',
          className
        )}
      />
      {showSuggestions && filteredVars.length > 0 && (
        <div className="absolute z-50 mt-1 w-72 rounded-md border bg-popover shadow-lg">
          <div className="text-xs text-muted-foreground border-b px-3 py-1.5">
            可用变量 (Tab/Enter 选择)
          </div>
          <div className="max-h-60 overflow-auto py-1">
            {filteredVars.map((v, i) => (
              <button
                key={v.name}
                onClick={() => insertVariable(v.name)}
                className={cn(
                  'w-full px-3 py-2 text-left hover:bg-accent transition-colors',
                  i === suggestionIndex && 'bg-accent'
                )}
              >
                <code className="text-sm font-semibold text-primary block">{`{{${v.name}}}`}</code>
                <span className="text-xs text-muted-foreground block mt-0.5 truncate">{v.desc}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ==================== Prompt Editor Component ====================

function PromptEditor({
  prompt,
  onSave,
  variables = [],
  models = [],
  defaultModel = '',
}: {
  prompt: PromptConfig
  onSave: (field: string, update: PromptConfigUpdate) => Promise<void>
  variables?: PromptVariable[]
  models?: LLMModelInfo[]
  defaultModel?: string
}) {
  const { field, system, user, description, model } = prompt
  // 如果 YAML 中 model.name 为空，使用 defaultModel（第一个模型 claude）
  const effectiveModelName = model.name || defaultModel
  // 保存后的基准值
  const [savedSystem, setSavedSystem] = useState(system)
  const [savedUser, setSavedUser] = useState(user)
  const [savedModel, setSavedModel] = useState({ ...model, name: effectiveModelName })
  // 当前编辑值
  const [systemPrompt, setSystemPrompt] = useState(system)
  const [userPrompt, setUserPrompt] = useState(user)
  const [modelName, setModelName] = useState(effectiveModelName)
  const [temperature, setTemperature] = useState(model.temperature)
  const [maxTokens, setMaxTokens] = useState(model.max_tokens)
  const [copied, setCopied] = useState(false)
  const [saving, setSaving] = useState(false)

  const isPromptModified = systemPrompt !== savedSystem || userPrompt !== savedUser
  const isModelModified = modelName !== savedModel.name ||
    temperature !== savedModel.temperature ||
    maxTokens !== savedModel.max_tokens
  const isModified = isPromptModified || isModelModified

  const handleCopy = async () => {
    const text = `System:\n${systemPrompt}\n\nUser:\n${userPrompt}`
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(field, {
        system: systemPrompt,
        user: userPrompt,
        model: {
          name: modelName,
          temperature,
          max_tokens: maxTokens,
        },
      })
      setSavedSystem(systemPrompt)
      setSavedUser(userPrompt)
      setSavedModel({ name: modelName, temperature, max_tokens: maxTokens })
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setSystemPrompt(savedSystem)
    setUserPrompt(savedUser)
    setModelName(savedModel.name)
    setTemperature(savedModel.temperature)
    setMaxTokens(savedModel.max_tokens)
  }

  return (
    <div className={cn(
      'border rounded-lg p-4 space-y-4',
      isModified && 'border-yellow-500/50'
    )}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Settings className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">
            {FIELD_LABELS[field] || field}
            {isModified && <span className="text-yellow-500 ml-1">*</span>}
          </span>
          {description && (
            <span className="text-xs text-muted-foreground">({description})</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleCopy}
            className="rounded p-1.5 hover:bg-muted"
            title="复制"
          >
            {copied ? (
              <Check className="h-4 w-4 text-green-600" />
            ) : (
              <Copy className="h-4 w-4 text-muted-foreground" />
            )}
          </button>
        </div>
      </div>

      {/* Model Configuration */}
      <div className="bg-muted/30 rounded-lg p-3">
        <div className="text-xs text-muted-foreground mb-2 font-medium">模型配置</div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-muted-foreground block mb-1">模型</label>
            <select
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
            >
              {models.map((m) => (
                <option key={m.key} value={m.key}>
                  {m.key} ({m.model})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">温度 (0-2)</label>
            <input
              type="number"
              value={temperature}
              onChange={(e) => setTemperature(Number(e.target.value))}
              min={0}
              max={2}
              step={0.1}
              className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground block mb-1">Max Tokens</label>
            <input
              type="number"
              value={maxTokens}
              onChange={(e) => setMaxTokens(Number(e.target.value))}
              min={1}
              max={65536}
              className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
            />
          </div>
        </div>
      </div>

      {/* Prompt Content */}
      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-1 block">System Prompt</label>
          <VariableTextarea
            value={systemPrompt}
            onChange={setSystemPrompt}
            minRows={4}
            variables={variables}
          />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">User Prompt</label>
          <VariableTextarea
            value={userPrompt}
            onChange={setUserPrompt}
            minRows={2}
            variables={variables}
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2 border-t">
        <button
          onClick={handleReset}
          disabled={!isModified || saving}
          className="text-sm text-muted-foreground hover:text-foreground px-3 py-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          重置
        </button>
        <button
          onClick={handleSave}
          disabled={!isModified || saving}
          className="text-sm bg-primary text-primary-foreground hover:bg-primary/90 px-3 py-1.5 rounded-md disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
        >
          {saving && <Loader2 className="h-3 w-3 animate-spin" />}
          保存
        </button>
      </div>
    </div>
  )
}

// ==================== Fill Tab ====================

function FillProgressPanel({
  progress,
  logs,
  onClose,
  onCancel,
  isCancelling,
}: {
  progress: FillProgress
  logs: FillLog[]
  onClose: () => void
  onCancel: () => void
  isCancelling: boolean
}) {
  const logsEndRef = useRef<HTMLDivElement>(null)

  // 自动滚动到底部
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs.length])

  const isRunning = progress.status === 'running' || progress.status === 'pending'
  const isCompleted = progress.status === 'completed'
  const isFailed = progress.status === 'failed'
  const isCancelled = progress.status === 'cancelled'

  const progressPercent = Math.round(progress.progress || 0)
  const currentNum = progress.current_step_num || 0
  const totalSteps = progress.total_steps || 0

  // 统计成功和失败数量
  // 优先使用后端返回的完成状态中的计数（切换页面回来时 logs 可能为空）
  const completedData = progress.data?.type === 'completed' ? progress.data : null
  const successCount = completedData?.success_count ?? logs.filter((l) => l.success).length
  const failCount = completedData?.fail_count ?? logs.filter((l) => !l.success).length

  return (
    <div className="rounded-lg border bg-card p-4 mt-4 space-y-4">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isRunning && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
          {isCompleted && <CheckCircle2 className="h-4 w-4 text-green-500" />}
          {isFailed && <XCircle className="h-4 w-4 text-red-500" />}
          {isCancelled && <XCircle className="h-4 w-4 text-orange-500" />}
          <span className="text-sm font-medium">
            {isRunning && '填充进行中...'}
            {isCompleted && '填充完成'}
            {isFailed && '填充失败'}
            {isCancelled && '已停止'}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            {currentNum} / {totalSteps}
          </span>
          {isRunning && (
            <button
              onClick={onCancel}
              disabled={isCancelling}
              className="flex items-center gap-1 text-sm text-orange-600 hover:text-orange-700 disabled:opacity-50"
            >
              {isCancelling ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Square className="h-3 w-3" />
              )}
              停止
            </button>
          )}
          {!isRunning && (
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* 进度条 */}
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div
          className={cn(
            'h-full transition-all duration-300',
            isFailed ? 'bg-red-500' : isCancelled ? 'bg-orange-500' : 'bg-primary'
          )}
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* 统计 */}
      <div className="flex items-center gap-4 text-sm">
        <span className="text-green-600">成功: {successCount}</span>
        <span className="text-red-600">失败: {failCount}</span>
        {progress.current_step && (
          <span className="text-muted-foreground">
            当前字段: {FIELD_LABELS[progress.current_step] || progress.current_step}
          </span>
        )}
      </div>

      {/* 日志列表 */}
      <div className="max-h-64 overflow-y-auto space-y-1 text-sm font-mono bg-muted/30 rounded-md p-3">
        {logs.length === 0 ? (
          <p className="text-muted-foreground">
            {isRunning ? '等待任务开始...' : isCompleted ? '任务已完成 (日志在页面切换后不保留)' : '暂无日志'}
          </p>
        ) : (
          logs.map((log, i) => (
            <div
              key={i}
              className={cn(
                'flex items-start gap-2 py-0.5',
                log.success ? 'text-green-600' : 'text-red-600'
              )}
            >
              {log.success ? (
                <Check className="h-3 w-3 mt-0.5 flex-shrink-0" />
              ) : (
                <X className="h-3 w-3 mt-0.5 flex-shrink-0" />
              )}
              <span className="flex-shrink-0">{log.factor}</span>
              <span className="text-muted-foreground flex-shrink-0">
                ({FIELD_LABELS[log.field] || log.field})
              </span>
              {log.error && (
                <span className="text-red-500 truncate" title={log.error}>
                  : {log.error}
                </span>
              )}
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>

      {/* 失败时显示错误信息 */}
      {isFailed && progress.error && (
        <div className="text-sm text-red-500 bg-red-50 dark:bg-red-950/20 rounded-md p-3">
          {progress.error}
        </div>
      )}
    </div>
  )
}

function FillTab({ status }: { status?: PipelineStatus }) {
  const queryClient = useQueryClient()
  const [selectedFields, setSelectedFields] = useState<FillableField[]>([])
  const [fillMode, setFillMode] = useState<FillMode>('incremental')
  const [delay, setDelay] = useState(15)
  const [concurrency, setConcurrency] = useState(1)
  const [taskId, setTaskId] = useState<string | null>(null)

  // 挂载时查询活跃任务
  const { data: activeTask } = useQuery({
    queryKey: ['pipeline-fill-active'],
    queryFn: pipelineApi.getActiveFillTask,
    refetchOnWindowFocus: false,
    staleTime: 0, // 始终查询最新状态
  })

  // 发现活跃任务时自动恢复
  useEffect(() => {
    if (activeTask?.task_id && !taskId) {
      setTaskId(activeTask.task_id)
    }
  }, [activeTask, taskId])

  const { progress, logs, isRunning, isCompleted, reset } = useFillProgress(taskId)

  const fillMutation = useMutation({
    mutationFn: (request: FillRequest) => pipelineApi.fill(request),
    onSuccess: (data) => {
      // 如果返回了 task_id，说明是异步任务
      if (data.task_id) {
        setTaskId(data.task_id)
      }
      queryClient.invalidateQueries({ queryKey: ['pipeline-status'] })
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (id: string) => pipelineApi.cancelFillTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-status'] })
    },
  })

  // 任务完成后刷新状态
  useEffect(() => {
    if (isCompleted) {
      queryClient.invalidateQueries({ queryKey: ['pipeline-status'] })
    }
  }, [isCompleted, queryClient])

  const handleCancel = () => {
    if (taskId) {
      cancelMutation.mutate(taskId)
    }
  }

  const fieldOptions: { value: FillableField; label: string }[] = [
    { value: 'style', label: '风格分类' },
    { value: 'tags', label: '因子标签' },
    { value: 'formula', label: '计算公式' },
    { value: 'input_data', label: '输入数据' },
    { value: 'value_range', label: '值域范围' },
    { value: 'description', label: '因子描述' },
    { value: 'analysis', label: '因子分析' },
    { value: 'llm_score', label: 'LLM评分' },
  ]

  const handleToggleField = (field: FillableField) => {
    setSelectedFields((prev) =>
      prev.includes(field) ? prev.filter((f) => f !== field) : [...prev, field]
    )
  }

  const handleSelectAll = () => {
    if (selectedFields.length === fieldOptions.length) {
      setSelectedFields([])
    } else {
      setSelectedFields(fieldOptions.map((f) => f.value))
    }
  }

  const handleFill = async (dryRun: boolean = false) => {
    if (selectedFields.length === 0) return

    // 清除之前的任务状态
    if (!dryRun) {
      setTaskId(null)
      reset()
    }

    await fillMutation.mutateAsync({
      fields: selectedFields,
      mode: fillMode,
      delay,
      concurrency,
      dry_run: dryRun,
    })
  }

  const handleCloseProgress = () => {
    setTaskId(null)
    reset()
    // 清除缓存，避免下次挂载时自动恢复已关闭的任务
    queryClient.setQueryData(['pipeline-fill-active'], null)
  }

  const getFieldEmptyCount = (field: FillableField): number => {
    return status?.field_coverage?.[field]?.empty ?? 0
  }

  // 判断是否正在执行任务（mutation pending 或 SSE running）
  const isBusy = fillMutation.isPending || isRunning

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Sparkles className="h-5 w-5 text-primary" />
        <div>
          <h3 className="font-semibold">字段填充</h3>
          <p className="text-sm text-muted-foreground">使用 LLM 自动填充因子元数据字段</p>
        </div>
      </div>

      {/* Field Selection */}
      <div className="rounded-lg border bg-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium">选择要填充的字段</h4>
          <button
            onClick={handleSelectAll}
            disabled={isBusy}
            className="text-sm text-primary hover:underline disabled:opacity-50"
          >
            {selectedFields.length === fieldOptions.length ? '取消全选' : '全选'}
          </button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {fieldOptions.map(({ value, label }) => {
            const emptyCount = getFieldEmptyCount(value)
            const isSelected = selectedFields.includes(value)
            return (
              <button
                key={value}
                onClick={() => handleToggleField(value)}
                disabled={isBusy}
                className={cn(
                  'flex items-center justify-between rounded-lg border p-4 text-left transition-colors disabled:opacity-50',
                  isSelected
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/50'
                )}
              >
                <div>
                  <p className="text-sm font-medium">{label}</p>
                  <p className="text-xs text-muted-foreground">待填充: {emptyCount}</p>
                </div>
                {isSelected && <CheckCircle2 className="h-5 w-5 text-primary" />}
              </button>
            )
          })}
        </div>
      </div>

      {/* Options */}
      <div className="rounded-lg border bg-card p-6">
        <h4 className="text-sm font-medium mb-4">填充选项</h4>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <label className="text-sm text-muted-foreground">填充模式</label>
            <SearchableSelect
              options={FILL_MODE_OPTIONS}
              value={fillMode}
              onChange={(value) => setFillMode(value as FillMode)}
              className="mt-1"
              disabled={isBusy}
            />
          </div>
          <div>
            <label className="text-sm text-muted-foreground">请求间隔 (秒)</label>
            <input
              type="number"
              value={delay}
              onChange={(e) => setDelay(Number(e.target.value))}
              min={0}
              max={120}
              disabled={isBusy}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm disabled:opacity-50"
            />
          </div>
          <div>
            <label className="text-sm text-muted-foreground">并发数</label>
            <input
              type="number"
              value={concurrency}
              onChange={(e) => setConcurrency(Number(e.target.value))}
              min={1}
              max={10}
              disabled={isBusy}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm disabled:opacity-50"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 mt-6">
          <button
            onClick={() => handleFill(true)}
            disabled={selectedFields.length === 0 || isBusy}
            className="flex items-center gap-2 rounded-md border px-4 py-2 text-sm hover:bg-accent disabled:opacity-50"
          >
            预览
          </button>
          <button
            onClick={() => handleFill(false)}
            disabled={selectedFields.length === 0 || isBusy}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {isBusy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            开始填充
          </button>
        </div>

        {/* Progress Panel (when task is running or completed) */}
        {taskId && progress && (
          <FillProgressPanel
            progress={progress}
            logs={logs}
            onClose={handleCloseProgress}
            onCancel={handleCancel}
            isCancelling={cancelMutation.isPending}
          />
        )}

        {/* Dry run result */}
        {fillMutation.data?.dry_run && (
          <div className="rounded-lg bg-muted/50 p-4 mt-4">
            <h4 className="text-sm font-medium mb-2">预览结果</h4>
            <div className="text-sm text-muted-foreground space-y-1">
              <p>总因子数: {fillMutation.data.total_factors}</p>
              <p>字段: {fillMutation.data.fields.join(', ')}</p>
              {fillMutation.data.to_fill && (
                <div>
                  待填充数量:
                  <ul className="list-disc list-inside ml-2">
                    {Object.entries(fillMutation.data.to_fill).map(([field, count]) => (
                      <li key={field}>
                        {FIELD_LABELS[field] || field}: {count as number}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ==================== Review Tab ====================

function ReviewTab() {
  const queryClient = useQueryClient()
  const [selectedFields, setSelectedFields] = useState<string[]>(['style', 'formula'])
  const [delay, setDelay] = useState(15)
  const [concurrency, setConcurrency] = useState(1)

  const reviewMutation = useMutation({
    mutationFn: (request: ReviewRequest) => pipelineApi.review(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-status'] })
    },
  })

  const fieldOptions = [
    { value: 'style', label: '风格分类' },
    { value: 'tags', label: '因子标签' },
    { value: 'formula', label: '计算公式' },
    { value: 'input_data', label: '输入数据' },
    { value: 'value_range', label: '值域范围' },
    { value: 'description', label: '因子描述' },
  ]

  const handleReview = async (dryRun: boolean = false) => {
    await reviewMutation.mutateAsync({
      fields: selectedFields,
      delay,
      concurrency,
      dry_run: dryRun,
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Zap className="h-5 w-5 text-primary" />
        <div>
          <h3 className="font-semibold">质量审核</h3>
          <p className="text-sm text-muted-foreground">使用 LLM 审核和优化已填充的字段内容</p>
        </div>
      </div>

      {/* Field Selection */}
      <div className="rounded-lg border bg-card p-6 space-y-4">
        <h4 className="text-sm font-medium">选择要审核的字段</h4>
        <div className="flex flex-wrap gap-2">
          {fieldOptions.map(({ value, label }) => (
            <button
              key={value}
              onClick={() =>
                setSelectedFields((prev) =>
                  prev.includes(value) ? prev.filter((f) => f !== value) : [...prev, value]
                )
              }
              className={cn(
                'rounded-full px-4 py-2 text-sm border transition-colors',
                selectedFields.includes(value)
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border hover:border-primary/50'
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Options */}
      <div className="rounded-lg border bg-card p-6">
        <h4 className="text-sm font-medium mb-4">审核选项</h4>
        <div className="grid grid-cols-2 gap-6 max-w-md">
          <div>
            <label className="text-sm text-muted-foreground">请求间隔 (秒)</label>
            <input
              type="number"
              value={delay}
              onChange={(e) => setDelay(Number(e.target.value))}
              min={0}
              max={120}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-sm text-muted-foreground">并发数</label>
            <input
              type="number"
              value={concurrency}
              onChange={(e) => setConcurrency(Number(e.target.value))}
              min={1}
              max={10}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 mt-6">
          <button
            onClick={() => handleReview(true)}
            disabled={selectedFields.length === 0 || reviewMutation.isPending}
            className="flex items-center gap-2 rounded-md border px-4 py-2 text-sm hover:bg-accent disabled:opacity-50"
          >
            预览
          </button>
          <button
            onClick={() => handleReview(false)}
            disabled={selectedFields.length === 0 || reviewMutation.isPending}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {reviewMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            开始审核
          </button>
        </div>

        {/* Result */}
        {reviewMutation.data && (
          <div className="rounded-lg bg-muted/50 p-4 mt-4">
            <h4 className="text-sm font-medium mb-2">
              {reviewMutation.data.reviewed === 0 ? '预览结果' : '审核结果'}
            </h4>
            <div className="text-sm text-muted-foreground space-y-1">
              <p>总数: {reviewMutation.data.total}</p>
              <p>已审核: {reviewMutation.data.reviewed}</p>
              <p>已修订: {reviewMutation.data.revised}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ==================== Review Prompt Editor ====================

function ReviewPromptEditor({ variables = [] }: { variables?: PromptVariable[] }) {
  const [savedSystem, setSavedSystem] = useState(REVIEW_PROMPT.system)
  const [systemPrompt, setSystemPrompt] = useState(REVIEW_PROMPT.system)
  const [copied, setCopied] = useState(false)

  const isModified = systemPrompt !== savedSystem

  const handleCopy = async () => {
    await navigator.clipboard.writeText(systemPrompt)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSave = () => {
    console.log('Saving review prompt:', { system: systemPrompt })
    setSavedSystem(systemPrompt)
  }

  const handleReset = () => {
    setSystemPrompt(savedSystem)
  }

  return (
    <div className={cn(
      'border rounded-lg p-4 space-y-4',
      isModified && 'border-yellow-500/50'
    )}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Settings className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">
            质量审核
            {isModified && <span className="text-yellow-500 ml-1">*</span>}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="rounded p-1.5 hover:bg-muted"
          title="复制"
        >
          {copied ? (
            <Check className="h-4 w-4 text-green-600" />
          ) : (
            <Copy className="h-4 w-4 text-muted-foreground" />
          )}
        </button>
      </div>

      <div>
        <label className="text-sm font-medium mb-1 block">System Prompt</label>
        <VariableTextarea
          value={systemPrompt}
          onChange={setSystemPrompt}
          minRows={6}
          variables={variables}
        />
      </div>

      <div className="flex justify-end gap-2 pt-2 border-t">
        <button
          onClick={handleReset}
          disabled={!isModified}
          className="text-sm text-muted-foreground hover:text-foreground px-3 py-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          重置
        </button>
        <button
          onClick={handleSave}
          disabled={!isModified}
          className="text-sm bg-primary text-primary-foreground hover:bg-primary/90 px-3 py-1.5 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
        >
          保存
        </button>
      </div>
    </div>
  )
}

// ==================== Prompts Tab ====================

function PromptsTab() {
  const queryClient = useQueryClient()

  // 从后端加载 prompt 配置
  const { data: prompts, isLoading, error, refetch } = useQuery({
    queryKey: ['pipeline-prompts'],
    queryFn: pipelineApi.getPrompts,
  })

  // 从后端加载可用变量（与 Factor 模型字段同步）
  const { data: variables = [] } = useQuery({
    queryKey: ['pipeline-variables'],
    queryFn: pipelineApi.getVariables,
  })

  // 从后端加载可用 LLM 模型列表
  const { data: modelsData } = useQuery({
    queryKey: ['pipeline-models'],
    queryFn: pipelineApi.getModels,
  })

  // 更新 prompt 配置
  const updateMutation = useMutation({
    mutationFn: ({ field, update }: { field: string; update: PromptConfigUpdate }) =>
      pipelineApi.updatePrompt(field, update),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-prompts'] })
    },
  })

  const handleSave = async (field: string, update: PromptConfigUpdate) => {
    await updateMutation.mutateAsync({ field, update })
  }

  // 按 FIELD_ORDER 排序
  const sortedPrompts = prompts?.slice().sort((a, b) => {
    const aIndex = FIELD_ORDER.indexOf(a.field)
    const bIndex = FIELD_ORDER.indexOf(b.field)
    return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex)
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Settings className="h-5 w-5 text-primary" />
          <div>
            <h3 className="font-semibold">Prompt 配置</h3>
            <p className="text-sm text-muted-foreground">
              管理字段填充和审核的 Prompt 模板，使用 {'{{'} variable {'}}'} 语法引用变量
            </p>
          </div>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
          刷新
        </button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-muted-foreground">加载 Prompt 配置...</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="flex items-center gap-2 p-4 border border-destructive/50 rounded-lg bg-destructive/10">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <span className="text-sm text-destructive">
            加载失败: {error instanceof Error ? error.message : '未知错误'}
          </span>
        </div>
      )}

      {/* Field Prompts */}
      {sortedPrompts && sortedPrompts.length > 0 && (
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-muted-foreground">
            字段填充 Prompt ({sortedPrompts.length} 个配置)
          </h4>
          {sortedPrompts.map((prompt) => (
            <PromptEditor
              key={prompt.field}
              prompt={prompt}
              onSave={handleSave}
              variables={variables}
              models={modelsData?.models || []}
              defaultModel={modelsData?.default || ''}
            />
          ))}
        </div>
      )}

      {/* Review Prompt */}
      <div className="space-y-4">
        <h4 className="text-sm font-medium text-muted-foreground">审核 Prompt</h4>
        <ReviewPromptEditor variables={variables} />
      </div>
    </div>
  )
}

// ==================== Main Component ====================

const TAB_CONFIG: { value: TabType; label: string; icon: LucideIcon }[] = [
  { value: 'ingest', label: '因子入库', icon: FolderInput },
  { value: 'fill', label: '字段填充', icon: PenLine },
  { value: 'review', label: '质量审核', icon: ClipboardCheck },
  { value: 'prompts', label: 'Prompt 配置', icon: Settings },
]

export function Component() {
  const [activeTab, setActiveTab] = useState<TabType>('ingest')

  const { data: status } = useQuery({
    queryKey: ['pipeline-status'],
    queryFn: pipelineApi.getStatus,
  })

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex items-center gap-4 border-b">
        {TAB_CONFIG.map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            onClick={() => setActiveTab(value)}
            className={cn(
              'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
              activeTab === value
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'ingest' && <IngestTab />}
      {activeTab === 'fill' && <FillTab status={status} />}
      {activeTab === 'review' && <ReviewTab />}
      {activeTab === 'prompts' && <PromptsTab />}
    </div>
  )
}
