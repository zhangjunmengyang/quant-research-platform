/**
 * Task Create View Component
 * 创建任务视图组件
 */

import { useState, useEffect } from 'react'
import {
  Loader2,
  Plus,
  Settings,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import {
  useBacktestTemplates,
  useBacktestConfig,
  useTaskMutations,
  createDefaultBacktestRequest,
  createDefaultStrategyItem,
  createDefaultFactorItem,
} from '@/features/strategy'
import { SearchableSelect } from '@/components/ui/SearchableSelect'
import { cn } from '@/lib/utils'
import type { BacktestRequest, StrategyItem, FactorItem } from '@/features/strategy'
import { ACCOUNT_TYPE_OPTIONS } from './constants'
import { StrategyConfigCard } from './StrategyConfigCard'

export interface TaskCreateViewProps {
  onBack: () => void
  onCreated: (id: string) => void
}

export function TaskCreateView({ onBack, onCreated }: TaskCreateViewProps) {
  const { data: templates = [], isLoading: templatesLoading } = useBacktestTemplates()
  const { data: config } = useBacktestConfig()
  const { createTask } = useTaskMutations()

  const [formData, setFormData] = useState<BacktestRequest>(createDefaultBacktestRequest())
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [newFactorName, setNewFactorName] = useState('')

  // Use server config for defaults
  useEffect(() => {
    if (config) {
      setFormData((prev) => ({
        ...prev,
        start_date: config.start_date,
        end_date: config.end_date,
        initial_usdt: config.initial_usdt,
        leverage: config.leverage,
        margin_rate: config.margin_rate,
        swap_c_rate: config.swap_c_rate,
        spot_c_rate: config.spot_c_rate,
        swap_min_order_limit: config.swap_min_order_limit,
        spot_min_order_limit: config.spot_min_order_limit,
        avg_price_col: config.avg_price_col as 'avg_price_1m' | 'avg_price_5m',
        min_kline_num: config.min_kline_num,
      }))
    }
  }, [config])

  const handleTemplateSelect = (templateName: string) => {
    const template = templates.find((t) => t.name === templateName)
    if (template) {
      setSelectedTemplate(templateName)
      setFormData((prev) => ({
        ...prev,
        name: template.name,
        strategy_list: template.strategy_list,
        leverage: template.default_config?.leverage ?? prev.leverage,
        initial_usdt: template.default_config?.initial_usdt ?? prev.initial_usdt,
      }))
    }
  }

  const handleAddStrategy = () => {
    const newStrategy = createDefaultStrategyItem()
    newStrategy.strategy = `Strategy_${formData.strategy_list.length + 1}`
    setFormData((prev) => ({
      ...prev,
      strategy_list: [...prev.strategy_list, newStrategy],
    }))
  }

  const handleRemoveStrategy = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      strategy_list: prev.strategy_list.filter((_, i) => i !== index),
    }))
  }

  const handleStrategyChange = (index: number, field: keyof StrategyItem, value: unknown) => {
    setFormData((prev) => ({
      ...prev,
      strategy_list: prev.strategy_list.map((stg, i) =>
        i === index ? { ...stg, [field]: value } : stg
      ),
    }))
  }

  const handleAddFactor = (strategyIndex: number) => {
    if (!newFactorName.trim()) return

    const factor = createDefaultFactorItem(newFactorName.trim())
    setFormData((prev) => ({
      ...prev,
      strategy_list: prev.strategy_list.map((stg, i) =>
        i === strategyIndex ? { ...stg, factor_list: [...stg.factor_list, factor] } : stg
      ),
    }))
    setNewFactorName('')
  }

  const handleRemoveFactor = (strategyIndex: number, factorIndex: number) => {
    setFormData((prev) => ({
      ...prev,
      strategy_list: prev.strategy_list.map((stg, i) =>
        i === strategyIndex
          ? { ...stg, factor_list: stg.factor_list.filter((_, j) => j !== factorIndex) }
          : stg
      ),
    }))
  }

  const handleFactorChange = (
    strategyIndex: number,
    factorIndex: number,
    field: keyof FactorItem,
    value: unknown
  ) => {
    setFormData((prev) => ({
      ...prev,
      strategy_list: prev.strategy_list.map((stg, i) =>
        i === strategyIndex
          ? {
              ...stg,
              factor_list: stg.factor_list.map((f, j) =>
                j === factorIndex ? { ...f, [field]: value } : f
              ),
            }
          : stg
      ),
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name || formData.strategy_list.length === 0) return

    const hasFactors = formData.strategy_list.every((stg) => stg.factor_list.length > 0)
    if (!hasFactors) return

    createTask.mutate(
      {
        name: formData.name,
        description: undefined,
        config: formData,
      },
      {
        onSuccess: (task) => {
          onCreated(task.id)
        },
      }
    )
  }

  const canSubmit =
    formData.name &&
    formData.strategy_list.length > 0 &&
    formData.strategy_list.every((stg) => stg.factor_list.length > 0)

  return (
    <>
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={onBack} className="rounded-md border p-2 hover:bg-accent">
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>
        <h1 className="text-xl font-semibold">创建回测任务</h1>
      </div>

      <form onSubmit={handleSubmit} className="grid gap-6 lg:grid-cols-3">
        {/* Left: Form */}
        <div className="space-y-6 lg:col-span-2">
          {/* Templates */}
          <div className="rounded-lg border bg-card p-6">
            <h3 className="mb-4 font-semibold">选择模板 (可选)</h3>
            {templatesLoading ? (
              <div className="flex h-20 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {templates.map((template) => (
                  <button
                    key={template.name}
                    type="button"
                    onClick={() => handleTemplateSelect(template.name)}
                    className={cn(
                      'rounded-lg border p-4 text-left transition-colors',
                      selectedTemplate === template.name
                        ? 'border-primary bg-primary/5'
                        : 'hover:bg-muted/50'
                    )}
                  >
                    <p className="font-medium">{template.name}</p>
                    {template.description && (
                      <p className="mt-1 text-sm text-muted-foreground">{template.description}</p>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Basic Config */}
          <div className="rounded-lg border bg-card p-6">
            <h3 className="mb-4 font-semibold">基本配置</h3>
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">任务名称 *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  placeholder="输入任务名称"
                  required
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium">开始日期</label>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, start_date: e.target.value }))
                    }
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    required
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">结束日期</label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData((prev) => ({ ...prev, end_date: e.target.value }))}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    required
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label className="mb-1 block text-sm font-medium">初始资金</label>
                  <input
                    type="number"
                    value={formData.initial_usdt}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        initial_usdt: parseFloat(e.target.value) || 10000,
                      }))
                    }
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    min="100"
                    step="100"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">杠杆倍数</label>
                  <input
                    type="number"
                    value={formData.leverage}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        leverage: parseFloat(e.target.value) || 1,
                      }))
                    }
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    min="0.1"
                    max="10"
                    step="0.1"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">账户类型</label>
                  <SearchableSelect
                    options={ACCOUNT_TYPE_OPTIONS}
                    value={formData.account_type}
                    onChange={(value) =>
                      setFormData((prev) => ({
                        ...prev,
                        account_type: value as '统一账户' | '普通账户',
                      }))
                    }
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Strategy List */}
          <div className="rounded-lg border bg-card p-6">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-semibold">策略配置 *</h3>
              <button
                type="button"
                onClick={handleAddStrategy}
                className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
              >
                <Plus className="h-3 w-3" />
                添加策略
              </button>
            </div>

            {formData.strategy_list.length === 0 ? (
              <p className="text-sm text-muted-foreground">请添加策略或选择模板</p>
            ) : (
              <div className="space-y-4">
                {formData.strategy_list.map((stg, stgIndex) => (
                  <StrategyConfigCard
                    key={stgIndex}
                    index={stgIndex}
                    strategy={stg}
                    availableFactors={config?.available_factors || []}
                    newFactorName={newFactorName}
                    onNewFactorNameChange={setNewFactorName}
                    onStrategyChange={handleStrategyChange}
                    onRemoveStrategy={handleRemoveStrategy}
                    onAddFactor={handleAddFactor}
                    onRemoveFactor={handleRemoveFactor}
                    onFactorChange={handleFactorChange}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Advanced Config */}
          <div className="rounded-lg border bg-card">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex w-full items-center justify-between p-4"
            >
              <div className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                <span className="font-medium">高级配置</span>
              </div>
              {showAdvanced ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>

            {showAdvanced && (
              <div className="space-y-4 border-t p-6">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-sm font-medium">合约手续费率</label>
                    <input
                      type="number"
                      value={formData.swap_c_rate}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          swap_c_rate: parseFloat(e.target.value) || 0.0006,
                        }))
                      }
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      step="0.0001"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium">现货手续费率</label>
                    <input
                      type="number"
                      value={formData.spot_c_rate}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          spot_c_rate: parseFloat(e.target.value) || 0.001,
                        }))
                      }
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      step="0.0001"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Summary & Submit */}
        <div className="space-y-6">
          <div className="rounded-lg border bg-card p-6 sticky top-6">
            <h3 className="mb-4 font-semibold">任务摘要</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">名称</span>
                <span className="font-medium">{formData.name || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">回测区间</span>
                <span className="font-medium">
                  {formData.start_date} ~ {formData.end_date}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">初始资金</span>
                <span className="font-medium">{formData.initial_usdt.toLocaleString()} USDT</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">杠杆倍数</span>
                <span className="font-medium">{formData.leverage}x</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">策略数量</span>
                <span className="font-medium">{formData.strategy_list.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">因子数量</span>
                <span className="font-medium">
                  {formData.strategy_list.reduce((acc, s) => acc + s.factor_list.length, 0)}
                </span>
              </div>
            </div>

            <div className="mt-6 space-y-2">
              <button
                type="submit"
                disabled={!canSubmit || createTask.isPending}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {createTask.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    创建中...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4" />
                    创建任务
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={onBack}
                className="w-full rounded-md border border-input px-4 py-2.5 text-sm font-medium hover:bg-accent"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      </form>
    </>
  )
}
