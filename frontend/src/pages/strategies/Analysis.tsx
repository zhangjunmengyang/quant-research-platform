/**
 * Strategy Analysis Page
 * 策略分析页 - 包含参数分析、选币相似度、资金曲线相关性、回测对比四个 Tab
 */

import { useState } from 'react'
import {
  BarChart3,
  GitCompare,
  Layers,
  LineChart as LineChartIcon,
  Loader2,
  Play,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useStrategies,
  useParamAnalysis,
  useCoinSimilarity,
  useEquityCorrelation,
  useBacktestComparison,
} from '@/features/strategy'
import type { ParamAnalysisRequest } from '@/features/strategy'
import { SearchableSelect, type SelectOption } from '@/components/ui/SearchableSelect'

type TabType = 'param' | 'coin' | 'equity' | 'backtest'

export function Component() {
  const [activeTab, setActiveTab] = useState<TabType>('param')

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex items-center gap-4 border-b">
        <button
          onClick={() => setActiveTab('param')}
          className={cn(
            'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'param'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <BarChart3 className="h-4 w-4" />
          参数分析
        </button>
        <button
          onClick={() => setActiveTab('coin')}
          className={cn(
            'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'coin'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <Layers className="h-4 w-4" />
          选币相似度
        </button>
        <button
          onClick={() => setActiveTab('equity')}
          className={cn(
            'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'equity'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <LineChartIcon className="h-4 w-4" />
          资金曲线相关性
        </button>
        <button
          onClick={() => setActiveTab('backtest')}
          className={cn(
            'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
            activeTab === 'backtest'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <GitCompare className="h-4 w-4" />
          回测对比
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'param' && <ParamAnalysisTab />}
      {activeTab === 'coin' && <CoinSimilarityTab />}
      {activeTab === 'equity' && <EquityCorrelationTab />}
      {activeTab === 'backtest' && <BacktestComparisonTab />}
    </div>
  )
}

// ============================================================================
// 参数分析 Tab
// ============================================================================

function ParamAnalysisTab() {
  const [travName, setTravName] = useState('')
  const [paramX, setParamX] = useState('')
  const [paramY, setParamY] = useState('')
  const [indicator, setIndicator] = useState('年化收益')
  const [limitDict, setLimitDict] = useState<Record<string, string>>({})

  const paramAnalysis = useParamAnalysis()

  const handleAnalyze = () => {
    if (!travName || !paramX) return

    const request: ParamAnalysisRequest = {
      trav_name: travName,
      param_x: paramX,
      param_y: paramY || undefined,
      indicator,
      limit_dict: Object.fromEntries(
        Object.entries(limitDict)
          .filter(([, v]) => v)
          .map(([k, v]) => [k, v.split(',').map((s) => s.trim())])
      ),
    }

    paramAnalysis.mutate(request)
  }

  const indicators = [
    '年化收益',
    '累计净值',
    '最大回撤',
    '收益回撤比',
    '夏普比率',
    '胜率',
  ]

  // 指标选项
  const indicatorOptions: SelectOption[] = indicators.map((ind) => ({
    value: ind,
    label: ind,
  }))

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 font-semibold">参数分析配置</h3>

        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-sm font-medium">遍历名称 *</label>
              <input
                type="text"
                value={travName}
                onChange={(e) => setTravName(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                placeholder="输入遍历任务名称"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">X轴参数 *</label>
              <input
                type="text"
                value={paramX}
                onChange={(e) => setParamX(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                placeholder="如: hold_period"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Y轴参数 (可选)</label>
              <input
                type="text"
                value={paramY}
                onChange={(e) => setParamY(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                placeholder="如: select_coin_num"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">指标</label>
              <SearchableSelect
                options={indicatorOptions}
                value={indicator}
                onChange={setIndicator}
                placeholder="选择指标"
              />
            </div>
          </div>

          {/* Limit Dict */}
          <div>
            <label className="mb-2 block text-sm font-medium">限制条件 (可选)</label>
            <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
              {['hold_period', 'market', 'select_coin_num'].map((key) => (
                <div key={key} className="flex items-center gap-2">
                  <span className="min-w-[120px] text-sm text-muted-foreground">{key}:</span>
                  <input
                    type="text"
                    value={limitDict[key] || ''}
                    onChange={(e) =>
                      setLimitDict((prev) => ({ ...prev, [key]: e.target.value }))
                    }
                    className="flex-1 rounded-md border border-input bg-background px-2 py-1 text-sm"
                    placeholder="逗号分隔"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Analyze Button */}
          <div className="flex justify-end">
            <button
              onClick={handleAnalyze}
              disabled={!travName || !paramX || paramAnalysis.isPending}
              className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {paramAnalysis.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  分析中...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  开始分析
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {paramAnalysis.isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-600">
          分析失败: {(paramAnalysis.error as Error)?.message}
        </div>
      )}

      {/* Results */}
      {paramAnalysis.data && (
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <h4 className="mb-2 font-medium">分析结果</h4>
            {paramAnalysis.data.html_path ? (
              <a
                href={`/api/v1/analysis/reports/${encodeURIComponent(paramAnalysis.data.html_path)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                查看分析报告 (热力图/平原图)
              </a>
            ) : (
              <p className="text-muted-foreground">分析完成，无报告生成</p>
            )}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!paramAnalysis.data && !paramAnalysis.isPending && (
        <div className="flex h-64 items-center justify-center rounded-lg border bg-card">
          <div className="text-center">
            <BarChart3 className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-2 text-muted-foreground">
              配置遍历名称和参数后点击"开始分析"
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// 选币相似度 Tab
// ============================================================================

function CoinSimilarityTab() {
  const { data: strategiesData } = useStrategies({ page_size: 100 })
  const strategies = strategiesData?.items || []

  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([])
  const [strategyToAdd, setStrategyToAdd] = useState('')
  const coinSimilarity = useCoinSimilarity()

  // 可选策略（排除已选）
  const availableStrategyOptions: SelectOption[] = strategies
    .filter((s) => !selectedStrategies.includes(s.id))
    .map((s) => ({
      value: s.id,
      label: s.name,
      description: s.description || undefined,
    }))

  const handleAddStrategy = (strategyId: string) => {
    if (!selectedStrategies.includes(strategyId) && selectedStrategies.length < 10) {
      setSelectedStrategies([...selectedStrategies, strategyId])
    }
  }

  const handleRemoveStrategy = (strategyId: string) => {
    setSelectedStrategies(selectedStrategies.filter((s) => s !== strategyId))
  }

  const handleAnalyze = () => {
    if (selectedStrategies.length < 2) return
    coinSimilarity.mutate({ strategy_list: selectedStrategies })
  }

  const getStrategyName = (id: string) => {
    return strategies.find((s) => s.id === id)?.name || id
  }

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 font-semibold">选币相似度分析 (最多10个策略)</h3>

        {/* Selected Strategies */}
        <div className="mb-4 flex flex-wrap gap-2">
          {selectedStrategies.length === 0 ? (
            <p className="text-sm text-muted-foreground">请从下方选择策略</p>
          ) : (
            selectedStrategies.map((id) => (
              <span
                key={id}
                className="flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1 text-sm"
              >
                {getStrategyName(id)}
                <button
                  onClick={() => handleRemoveStrategy(id)}
                  className="ml-1 rounded-full p-0.5 hover:bg-primary/20"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))
          )}
        </div>

        {/* Add Strategy */}
        <div className="flex items-center gap-4">
          <SearchableSelect
            options={availableStrategyOptions}
            value={strategyToAdd}
            onChange={(value) => {
              if (value) {
                handleAddStrategy(value)
                setStrategyToAdd('')
              }
            }}
            placeholder="添加策略..."
            searchPlaceholder="搜索策略..."
            emptyText="无匹配策略"
            disabled={selectedStrategies.length >= 10}
            className="flex-1"
          />

          <button
            onClick={handleAnalyze}
            disabled={selectedStrategies.length < 2 || coinSimilarity.isPending}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {coinSimilarity.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                分析中...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                计算相似度
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error */}
      {coinSimilarity.isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-600">
          分析失败: {(coinSimilarity.error as Error)?.message}
        </div>
      )}

      {/* Results */}
      {coinSimilarity.data && (
        <div className="space-y-4">
          {coinSimilarity.data.html_path && (
            <div className="rounded-lg border bg-card p-4">
              <a
                href={`/api/v1/analysis/reports/${encodeURIComponent(coinSimilarity.data.html_path)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                查看相似度热力图
              </a>
            </div>
          )}

          {coinSimilarity.data.similarity_matrix && (
            <div className="rounded-lg border bg-card p-6">
              <h4 className="mb-4 font-medium">相似度矩阵</h4>
              <SimilarityTable
                strategies={selectedStrategies.map(getStrategyName)}
                matrix={coinSimilarity.data.similarity_matrix}
              />
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!coinSimilarity.data && !coinSimilarity.isPending && (
        <div className="flex h-64 items-center justify-center rounded-lg border bg-card">
          <div className="text-center">
            <Layers className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-2 text-muted-foreground">
              选择至少2个策略后点击"计算相似度"
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// 资金曲线相关性 Tab
// ============================================================================

function EquityCorrelationTab() {
  const { data: strategiesData } = useStrategies({ page_size: 100 })
  const strategies = strategiesData?.items || []

  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([])
  const [strategyToAdd, setStrategyToAdd] = useState('')
  const equityCorrelation = useEquityCorrelation()

  // 可选策略（排除已选）
  const availableStrategyOptions: SelectOption[] = strategies
    .filter((s) => !selectedStrategies.includes(s.id))
    .map((s) => ({
      value: s.id,
      label: s.name,
      description: s.description || undefined,
    }))

  const handleAddStrategy = (strategyId: string) => {
    if (!selectedStrategies.includes(strategyId) && selectedStrategies.length < 10) {
      setSelectedStrategies([...selectedStrategies, strategyId])
    }
  }

  const handleRemoveStrategy = (strategyId: string) => {
    setSelectedStrategies(selectedStrategies.filter((s) => s !== strategyId))
  }

  const handleAnalyze = () => {
    if (selectedStrategies.length < 2) return
    equityCorrelation.mutate({ strategy_list: selectedStrategies })
  }

  const getStrategyName = (id: string) => {
    return strategies.find((s) => s.id === id)?.name || id
  }

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 font-semibold">资金曲线相关性分析 (最多10个策略)</h3>

        {/* Selected Strategies */}
        <div className="mb-4 flex flex-wrap gap-2">
          {selectedStrategies.length === 0 ? (
            <p className="text-sm text-muted-foreground">请从下方选择策略</p>
          ) : (
            selectedStrategies.map((id) => (
              <span
                key={id}
                className="flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1 text-sm"
              >
                {getStrategyName(id)}
                <button
                  onClick={() => handleRemoveStrategy(id)}
                  className="ml-1 rounded-full p-0.5 hover:bg-primary/20"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))
          )}
        </div>

        {/* Add Strategy */}
        <div className="flex items-center gap-4">
          <SearchableSelect
            options={availableStrategyOptions}
            value={strategyToAdd}
            onChange={(value) => {
              if (value) {
                handleAddStrategy(value)
                setStrategyToAdd('')
              }
            }}
            placeholder="添加策略..."
            searchPlaceholder="搜索策略..."
            emptyText="无匹配策略"
            disabled={selectedStrategies.length >= 10}
            className="flex-1"
          />

          <button
            onClick={handleAnalyze}
            disabled={selectedStrategies.length < 2 || equityCorrelation.isPending}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {equityCorrelation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                分析中...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                计算相关性
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error */}
      {equityCorrelation.isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-600">
          分析失败: {(equityCorrelation.error as Error)?.message}
        </div>
      )}

      {/* Results */}
      {equityCorrelation.data && (
        <div className="space-y-4">
          {equityCorrelation.data.html_path && (
            <div className="rounded-lg border bg-card p-4">
              <a
                href={`/api/v1/analysis/reports/${encodeURIComponent(equityCorrelation.data.html_path)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                查看相关性热力图
              </a>
            </div>
          )}

          {equityCorrelation.data.correlation_matrix && (
            <div className="rounded-lg border bg-card p-6">
              <h4 className="mb-4 font-medium">相关性矩阵</h4>
              <CorrelationTable
                strategies={selectedStrategies.map(getStrategyName)}
                matrix={equityCorrelation.data.correlation_matrix}
              />
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!equityCorrelation.data && !equityCorrelation.isPending && (
        <div className="flex h-64 items-center justify-center rounded-lg border bg-card">
          <div className="text-center">
            <LineChartIcon className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-2 text-muted-foreground">
              选择至少2个策略后点击"计算相关性"
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// 回测对比 Tab
// ============================================================================

function BacktestComparisonTab() {
  const [backtestName, setBacktestName] = useState('')
  const [startTime, setStartTime] = useState('')
  const [endTime, setEndTime] = useState('')

  const backtestComparison = useBacktestComparison()

  const handleCompare = () => {
    if (!backtestName) return

    backtestComparison.mutate({
      backtest_name: backtestName,
      start_time: startTime || undefined,
      end_time: endTime || undefined,
    })
  }

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 font-semibold">回测与实盘对比</h3>

        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm font-medium">回测名称 *</label>
              <input
                type="text"
                value={backtestName}
                onChange={(e) => setBacktestName(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                placeholder="输入回测任务名称"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">开始时间 (可选)</label>
              <input
                type="date"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">结束时间 (可选)</label>
              <input
                type="date"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
          </div>

          {/* Compare Button */}
          <div className="flex justify-end">
            <button
              onClick={handleCompare}
              disabled={!backtestName || backtestComparison.isPending}
              className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {backtestComparison.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  对比中...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  开始对比
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {backtestComparison.isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-600">
          对比失败: {(backtestComparison.error as Error)?.message}
        </div>
      )}

      {/* Results */}
      {backtestComparison.data && (
        <div className="space-y-4">
          {backtestComparison.data.html_path && (
            <div className="rounded-lg border bg-card p-4">
              <a
                href={`/api/v1/analysis/reports/${encodeURIComponent(backtestComparison.data.html_path)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                查看对比报告
              </a>
            </div>
          )}

          {backtestComparison.data.metrics_comparison && (
            <div className="rounded-lg border bg-card p-6">
              <h4 className="mb-4 font-medium">指标对比</h4>
              <div className="overflow-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="px-4 py-3 text-left text-sm font-medium">指标</th>
                      <th className="px-4 py-3 text-center text-sm font-medium">回测</th>
                      <th className="px-4 py-3 text-center text-sm font-medium">实盘</th>
                      <th className="px-4 py-3 text-center text-sm font-medium">差异</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {Object.entries(backtestComparison.data.metrics_comparison).map(
                      ([key, values]) => (
                        <tr key={key} className="hover:bg-muted/50">
                          <td className="px-4 py-3 font-medium">{key}</td>
                          <td className="px-4 py-3 text-center">
                            {typeof values.backtest === 'number'
                              ? values.backtest.toFixed(4)
                              : values.backtest}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {typeof values.live === 'number' ? values.live.toFixed(4) : values.live}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span
                              className={
                                typeof values.diff === 'number' && values.diff > 0
                                  ? 'text-green-600'
                                  : typeof values.diff === 'number' && values.diff < 0
                                    ? 'text-red-600'
                                    : ''
                              }
                            >
                              {typeof values.diff === 'number'
                                ? (values.diff > 0 ? '+' : '') + values.diff.toFixed(4)
                                : values.diff}
                            </span>
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!backtestComparison.data && !backtestComparison.isPending && (
        <div className="flex h-64 items-center justify-center rounded-lg border bg-card">
          <div className="text-center">
            <GitCompare className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-2 text-muted-foreground">
              输入回测名称后点击"开始对比"
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Helper Components
// ============================================================================

interface SimilarityTableProps {
  strategies: string[]
  matrix: number[][]
}

function SimilarityTable({ strategies, matrix }: SimilarityTableProps) {
  return (
    <div className="overflow-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-2 py-2 text-left font-medium"></th>
            {strategies.map((s, i) => (
              <th key={i} className="px-2 py-2 text-center font-medium">
                {s.slice(0, 10)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y">
          {strategies.map((s, i) => (
            <tr key={i} className="hover:bg-muted/50">
              <td className="px-2 py-2 font-medium">{s.slice(0, 10)}</td>
              {matrix[i]?.map((val, j) => (
                <td key={j} className="px-2 py-2 text-center">
                  <span
                    className={cn(
                      'rounded px-1.5 py-0.5 text-xs',
                      i === j
                        ? 'bg-gray-100'
                        : val >= 0.8
                          ? 'bg-red-100 text-red-800'
                          : val >= 0.6
                            ? 'bg-orange-100 text-orange-800'
                            : val >= 0.4
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-green-100 text-green-800'
                    )}
                  >
                    {val.toFixed(2)}
                  </span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

interface CorrelationTableProps {
  strategies: string[]
  matrix: number[][]
}

function CorrelationTable({ strategies, matrix }: CorrelationTableProps) {
  return (
    <div className="overflow-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-2 py-2 text-left font-medium"></th>
            {strategies.map((s, i) => (
              <th key={i} className="px-2 py-2 text-center font-medium">
                {s.slice(0, 10)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y">
          {strategies.map((s, i) => (
            <tr key={i} className="hover:bg-muted/50">
              <td className="px-2 py-2 font-medium">{s.slice(0, 10)}</td>
              {matrix[i]?.map((val, j) => (
                <td key={j} className="px-2 py-2 text-center">
                  <span
                    className={cn(
                      'rounded px-1.5 py-0.5 text-xs',
                      i === j
                        ? 'bg-gray-100'
                        : val >= 0.8
                          ? 'bg-red-100 text-red-800'
                          : val >= 0.5
                            ? 'bg-orange-100 text-orange-800'
                            : val >= 0.2
                              ? 'bg-yellow-100 text-yellow-800'
                              : val >= -0.2
                                ? 'bg-gray-100'
                                : 'bg-blue-100 text-blue-800'
                    )}
                  >
                    {val.toFixed(2)}
                  </span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
