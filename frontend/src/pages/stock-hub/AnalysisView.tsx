/**
 * 增强因子分析页 — 支持早盘换仓 + 全offset + HTML报告
 */

import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  BarChart3, Play, Info, Sparkles, Loader2,
  FileText, ExternalLink, ChevronDown, ChevronUp,
} from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { BaseChart } from '@/components/charts/BaseChart'

import {
  useStockHubStatus,
  useEnhancedAnalysis,
  useCachedFactors,
  useAvailableBacktests,
  useEvaluateFactor,
  useStockEvaluation,
  stockHubApi,
} from '@/features/stock-hub'
import type { EnhancedAnalysisData, FactorEvaluation } from '@/features/stock-hub'
import { StockHubNotConfigured } from './StockHubNotConfigured'

// ===== 预设分析配置 =====

const PERIOD_PRESETS = [
  { label: '5日单offset', value: ['5_0'], desc: '仅5_0' },
  { label: '5日全offset', value: ['5_0', '5_1', '5_2', '5_3', '5_4'], desc: '5_0~5_4' },
  { label: '周度单offset', value: ['W_0'], desc: '仅W_0' },
  { label: '周度全offset', value: ['W_0', 'W_1', 'W_2', 'W_3', 'W_4'], desc: 'W_0~W_4' },
]

const REBALANCE_OPTIONS = [
  { label: '0930 开盘', value: '0930' },
  { label: '0955', value: '0955' },
  { label: '1000', value: '1000' },
  { label: '1030', value: '1030' },
  { label: '1100', value: '1100' },
  { label: '1300', value: '1300' },
  { label: '1400', value: '1400' },
  { label: '1455', value: '1455' },
  { label: '收盘', value: 'close' },
  { label: '收盘-开盘', value: 'close-open' },
]

// ===== 核心指标卡片 =====

function MetricsCards({ data }: { data: EnhancedAnalysisData }) {
  const metrics = [
    {
      label: 'IC均值',
      value: data.ic_mean,
      format: (v: number) => v.toFixed(4),
      good: Math.abs(data.ic_mean) > 0.03,
    },
    {
      label: 'ICIR',
      value: data.icir,
      format: (v: number) => v.toFixed(4),
      good: Math.abs(data.icir) > 0.5,
    },
    {
      label: '|ICIR|',
      value: data.abs_icir,
      format: (v: number) => v.toFixed(4),
      good: data.abs_icir > 0.5,
    },
    {
      label: 'IC胜率',
      value: data.ic_ratio,
      format: (v: string) => v,
      good: parseFloat(data.ic_ratio) > 55,
      isString: true,
    },
    {
      label: '因子得分',
      value: data.score,
      format: (v: number) => v.toFixed(2),
      good: data.score > 1.0,
    },
  ]

  return (
    <div className="grid grid-cols-5 gap-2">
      {metrics.map((m) => (
        <Card key={m.label}>
          <CardContent className="p-3 text-center">
            <p className="text-xs text-muted-foreground">{m.label}</p>
            <p
              className={`text-xl font-bold ${
                m.good
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-muted-foreground'
              }`}
            >
              {m.isString ? m.format(m.value as string) : (m.format as (v: number) => string)(m.value as number)}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// ===== 分组净值柱状图 =====

function GroupValuesChart({ data }: { data: Record<string, number> }) {
  const option = useMemo(() => {
    const groups = Object.keys(data)
    const values = groups.map((g) => data[g] ?? 0)

    return {
      title: { text: '分组净值', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' as const },
      grid: { left: '8%', right: '4%', bottom: '12%', top: '18%' },
      xAxis: { type: 'category' as const, data: groups, axisLabel: { fontSize: 11 } },
      yAxis: { type: 'value' as const },
      series: [
        {
          type: 'bar' as const,
          data: values.map((v) => ({
            value: v,
            itemStyle: { color: v >= 1 ? '#22c55e' : '#ef4444' },
          })),
          barMaxWidth: 40,
          label: { show: true, position: 'top' as const, formatter: '{c}', fontSize: 10 },
        },
      ],
    }
  }, [data])

  return <BaseChart option={option} style={{ height: '300px' }} />
}

// ===== 风格暴露柱状图 =====

function StyleExposureChart({ data }: { data: Record<string, number> }) {
  const option = useMemo(() => {
    const styles = Object.keys(data)
    const values = styles.map((s) => data[s] ?? 0)

    return {
      title: { text: '风格暴露', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' as const },
      grid: { left: '12%', right: '4%', bottom: '15%', top: '18%' },
      xAxis: {
        type: 'category' as const,
        data: styles,
        axisLabel: { fontSize: 10, rotate: 30 },
      },
      yAxis: { type: 'value' as const, min: -1, max: 1 },
      series: [
        {
          type: 'bar' as const,
          data: values.map((v) => ({
            value: Number(v.toFixed(4)),
            itemStyle: { color: v >= 0 ? '#3b82f6' : '#ef4444' },
          })),
          barMaxWidth: 30,
        },
      ],
    }
  }, [data])

  return <BaseChart option={option} style={{ height: '300px' }} />
}

// ===== 因子选择器（从缓存列表） =====

function CachedFactorSelector({
  value,
  onChange,
  backtestName,
}: {
  value: string
  onChange: (name: string) => void
  backtestName?: string
}) {
  const { data, isLoading } = useCachedFactors(backtestName)
  const factors = data?.factors ?? []
  const [search, setSearch] = useState('')

  const filtered = search
    ? factors.filter((f) => f.toLowerCase().includes(search.toLowerCase()))
    : factors

  return (
    <div className="space-y-1">
      <label className="block text-xs text-muted-foreground">
        {isLoading ? '加载中...' : `可用因子 (${factors.length})`}
      </label>
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="搜索因子名..."
        className="h-8 w-full rounded-md border border-input bg-background px-2 text-sm"
      />
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
        size={6}
      >
        {filtered.map((f) => (
          <option key={f} value={f}>{f}</option>
        ))}
      </select>
    </div>
  )
}

// ===== AI 评估结果 =====

function scoreColor(score: number | null): string {
  if (score === null) return 'text-muted-foreground'
  if (score >= 4.0) return 'text-green-600 dark:text-green-400'
  if (score >= 3.0) return 'text-blue-600 dark:text-blue-400'
  if (score >= 2.0) return 'text-amber-600 dark:text-amber-400'
  return 'text-red-600 dark:text-red-400'
}

function scoreBg(score: number | null): string {
  if (score === null) return 'bg-muted'
  if (score >= 4.0) return 'bg-green-100 dark:bg-green-950'
  if (score >= 3.0) return 'bg-blue-100 dark:bg-blue-950'
  if (score >= 2.0) return 'bg-amber-100 dark:bg-amber-950'
  return 'bg-red-100 dark:bg-red-950'
}

function InlineEvaluationResult({ evaluation }: { evaluation: FactorEvaluation }) {
  const { t } = useTranslation()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 text-primary" />
          AI {t('stockHub.evaluation')}
          {evaluation.overall_score !== null && (
            <div className={`ml-auto flex h-8 w-8 items-center justify-center rounded-full ${scoreBg(evaluation.overall_score)}`}>
              <span className={`text-sm font-bold ${scoreColor(evaluation.overall_score)}`}>
                {evaluation.overall_score.toFixed(1)}
              </span>
            </div>
          )}
          {evaluation.verdict && (
            <Badge variant={evaluation.verdict === '推荐' ? 'success' : evaluation.verdict === '弃用' ? 'destructive' : 'warning'}>
              {evaluation.verdict}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 md:grid-cols-3">
          {evaluation.logic && (
            <div className="rounded-lg border p-3 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">逻辑</span>
                <span className={`text-lg font-bold ${scoreColor(evaluation.logic.score)}`}>
                  {evaluation.logic.score.toFixed(1)}
                </span>
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">{evaluation.logic.analysis}</p>
            </div>
          )}
          {evaluation.backtest && (
            <div className="rounded-lg border p-3 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">回测</span>
                <span className={`text-lg font-bold ${scoreColor(evaluation.backtest.score)}`}>
                  {evaluation.backtest.score.toFixed(1)}
                </span>
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">{evaluation.backtest.analysis}</p>
            </div>
          )}
          {evaluation.effectiveness && (
            <div className="rounded-lg border p-3 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">IC</span>
                <span className={`text-lg font-bold ${scoreColor(evaluation.effectiveness.score)}`}>
                  {evaluation.effectiveness.score.toFixed(1)}
                </span>
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">{evaluation.effectiveness.analysis}</p>
            </div>
          )}
        </div>
        {evaluation.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {evaluation.tags.map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
            ))}
          </div>
        )}
        {evaluation.overall_summary && (
          <div className="rounded-lg border p-3">
            <p className="text-sm leading-relaxed">{evaluation.overall_summary}</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ===== 主页面 =====

export function Component() {
  const { t } = useTranslation()
  const { data: status } = useStockHubStatus()
  const { data: backtestData } = useAvailableBacktests()
  const backtests = backtestData?.backtests ?? []

  // 回测数据源
  const [backtestName, setBacktestName] = useState<string>('')

  // 分析配置
  const [factorName, setFactorName] = useState('')
  const [periodPresetIdx, setPeriodPresetIdx] = useState(0)
  const [rebalanceTime, setRebalanceTime] = useState('0955')
  const [bins, setBins] = useState(10)
  const [showAdvanced, setShowAdvanced] = useState(false)

  // HTML报告展示
  const [showReport, setShowReport] = useState(false)

  const enhancedMutation = useEnhancedAnalysis()
  const evaluateMutation = useEvaluateFactor()
  const { data: existingEvaluation } = useStockEvaluation(factorName, !!factorName)

  const analysisData = enhancedMutation.data as EnhancedAnalysisData | undefined

  // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
  const currentPreset = PERIOD_PRESETS[periodPresetIdx]!

  const handleAnalyze = () => {
    if (!factorName) return
    enhancedMutation.mutate({
      factor_name: factorName,
      period_offset_list: currentPreset.value,
      rebalance_time: rebalanceTime,
      bins,
      ...(backtestName ? { backtest_name: backtestName } : {}),
    })
    setShowReport(false)
  }

  const handleEvaluate = () => {
    if (!factorName || !analysisData) return
    evaluateMutation.mutate({
      factor_name: factorName,
      ic_data: {
        ic_mean: analysisData.ic_mean,
        icir: analysisData.icir,
        ic_ratio: analysisData.ic_ratio,
        score: analysisData.score,
        group_values: analysisData.group_values,
        style_exposure: analysisData.style_exposure,
      },
    })
  }

  const evaluationResult: FactorEvaluation | null =
    (evaluateMutation.data as FactorEvaluation | undefined) ?? existingEvaluation ?? null

  const reportUrl = analysisData
    ? stockHubApi.getAnalysisReportUrl(
        analysisData.factor_name,
        currentPreset.value.join('+') + '+' + rebalanceTime
      )
    : null

  if (status && !status.available) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{t('stockHub.analysis')}</h1>
        <StockHubNotConfigured status={status} />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t('stockHub.analysis')}</h1>

      {/* ===== 分析配置 ===== */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BarChart3 className="h-4 w-4" />
            因子分析配置
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* 回测数据源 */}
          <div>
            <label className="block text-xs text-muted-foreground mb-1">回测数据源</label>
            <select
              value={backtestName}
              onChange={(e) => { setBacktestName(e.target.value); setFactorName('') }}
              className="h-8 w-full max-w-md rounded-md border border-input bg-background px-2 text-sm"
            >
              <option value="">默认（框架config.py）</option>
              {backtests.map((bt) => (
                <option key={bt.name} value={bt.name}>
                  {bt.name}（{bt.factor_count}因子，{bt.modified_time}）
                </option>
              ))}
            </select>
          </div>

          {/* 因子选择 */}
          <div className="grid grid-cols-2 gap-4">
            <CachedFactorSelector value={factorName} onChange={setFactorName} backtestName={backtestName || undefined} />
            <div className="space-y-2">
              {/* 分析周期预设 */}
              <div>
                <label className="block text-xs text-muted-foreground mb-1">分析周期</label>
                <div className="flex flex-wrap gap-1">
                  {PERIOD_PRESETS.map((preset, idx) => (
                    <Button
                      key={preset.label}
                      variant={periodPresetIdx === idx ? 'default' : 'outline'}
                      size="sm"
                      className="text-xs"
                      onClick={() => setPeriodPresetIdx(idx)}
                    >
                      {preset.label}
                    </Button>
                  ))}
                </div>
                <p className="text-2xs text-muted-foreground mt-1">
                  {currentPreset.desc}
                </p>
              </div>

              {/* 换仓时间 */}
              <div>
                <label className="block text-xs text-muted-foreground mb-1">换仓时间</label>
                <div className="flex flex-wrap gap-1">
                  {REBALANCE_OPTIONS.map((opt) => (
                    <Button
                      key={opt.value}
                      variant={rebalanceTime === opt.value ? 'default' : 'outline'}
                      size="sm"
                      className="text-xs"
                      onClick={() => setRebalanceTime(opt.value)}
                    >
                      {opt.label}
                    </Button>
                  ))}
                </div>
              </div>

              {/* 高级选项 */}
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                {showAdvanced ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                高级选项
              </button>
              {showAdvanced && (
                <div className="flex gap-3">
                  <div>
                    <label className="block text-xs text-muted-foreground">分组数</label>
                    <input
                      type="number"
                      value={bins}
                      onChange={(e) => setBins(Number(e.target.value))}
                      className="h-8 w-20 rounded-md border border-input bg-background px-2 text-sm"
                      min={2} max={20}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 提交按钮 */}
          <div className="flex items-center gap-3">
            <Button
              onClick={handleAnalyze}
              loading={enhancedMutation.isPending}
              disabled={!factorName}
              className="gap-1"
            >
              <Play className="h-4 w-4" />
              开始分析
            </Button>
            {factorName && (
              <span className="text-xs text-muted-foreground">
                {factorName} | {currentPreset.desc} | {rebalanceTime}
              </span>
            )}
            {enhancedMutation.isError && (
              <Badge variant="destructive" className="text-xs">
                {(enhancedMutation.error as Error).message}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* ===== 分析结果 ===== */}
      {analysisData && (
        <div className="space-y-4">
          {/* 结果头部信息 */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Badge variant="outline">{analysisData.factor_name}</Badge>
            <span>{analysisData.start_date} ~ {analysisData.end_date}</span>
            <span>|</span>
            <span>周期: {analysisData.period_offset_list.join(',')}</span>
            <span>|</span>
            <span>换仓: {analysisData.rebalance_time}</span>
            <span>|</span>
            <span>耗时: {analysisData.elapsed_seconds}s</span>
          </div>

          {/* 核心指标 */}
          <MetricsCards data={analysisData} />

          {/* 图表区 */}
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardContent className="p-3">
                <GroupValuesChart data={analysisData.group_values} />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-3">
                <StyleExposureChart data={analysisData.style_exposure} />
              </CardContent>
            </Card>
          </div>

          {/* HTML完整报告 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4" />
                完整分析报告
                <div className="ml-auto flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowReport(!showReport)}
                    className="text-xs gap-1"
                  >
                    {showReport ? '收起' : '展开报告'}
                    {showReport ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  </Button>
                  {reportUrl && (
                    <a href={reportUrl} target="_blank" rel="noopener noreferrer">
                      <Button variant="ghost" size="sm" className="text-xs gap-1">
                        <ExternalLink className="h-3 w-3" />
                        新窗口
                      </Button>
                    </a>
                  )}
                </div>
              </CardTitle>
            </CardHeader>
            {showReport && reportUrl && (
              <CardContent className="p-0">
                <iframe
                  src={reportUrl}
                  className="w-full border-0"
                  style={{ height: '800px' }}
                  title="Factor Analysis Report"
                />
              </CardContent>
            )}
          </Card>

          {/* AI 评估 */}
          <div className="flex items-center gap-3">
            <Button
              onClick={handleEvaluate}
              disabled={evaluateMutation.isPending}
              variant="outline"
              className="gap-2"
            >
              {evaluateMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {evaluateMutation.isPending ? t('stockHub.evaluating') : t('stockHub.aiEvaluate')}
            </Button>
            {evaluateMutation.isError && (
              <Badge variant="destructive">
                {(evaluateMutation.error as Error).message}
              </Badge>
            )}
          </div>

          {evaluationResult && <InlineEvaluationResult evaluation={evaluationResult} />}
        </div>
      )}

      {/* 空状态 */}
      {!analysisData && !enhancedMutation.isPending && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <BarChart3 className="mx-auto h-12 w-12 mb-3 text-muted-foreground/30" />
            <p>选择因子并配置分析参数，点击"开始分析"</p>
            <p className="text-xs mt-1">
              <Info className="inline h-3 w-3 mr-1" />
              需要先运行过回测，运行缓存中才会有可分析的因子
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
