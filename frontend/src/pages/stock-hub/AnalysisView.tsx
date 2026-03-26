/**
 * Stock Hub - 单因子IC分析页
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Play } from 'lucide-react'
import {
  useStockStatus,
  useAvailableBacktests,
  useCachedFactors,
  useEnhancedAnalysis,
  PERIOD_PRESETS,
  REBALANCE_TIMES,
} from '@/features/stock-hub'
import type { AnalysisResult } from '@/features/stock-hub'

export function Component() {
  const { t } = useTranslation()
  const { data: status, isLoading: statusLoading } = useStockStatus()
  const { data: backtestsData } = useAvailableBacktests()

  const [backtestName, setBacktestName] = useState<string>('')
  const [selectedFactor, setSelectedFactor] = useState('')
  const [periodPreset, setPeriodPreset] = useState<keyof typeof PERIOD_PRESETS>('5日单offset')
  const [rebalanceTime, setRebalanceTime] = useState('0955')
  const [bins, setBins] = useState(10)
  const [result, setResult] = useState<AnalysisResult | null>(null)

  const { data: cachedFactors } = useCachedFactors(backtestName || undefined)
  const analysisMutation = useEnhancedAnalysis()

  if (statusLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  if (!status?.available) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4 text-muted-foreground">
        <p className="text-lg font-medium">{t('stockHub.notConfigured')}</p>
        <p className="text-sm">{t('stockHub.notConfiguredHint')}</p>
      </div>
    )
  }

  const backtests = backtestsData?.backtests ?? []
  const factors = cachedFactors ?? []

  const handleAnalysis = () => {
    if (!selectedFactor) return
    analysisMutation.mutate(
      {
        factor_name: selectedFactor,
        period_offset_list: [...PERIOD_PRESETS[periodPreset]],
        rebalance_time: rebalanceTime,
        bins,
        backtest_name: backtestName || undefined,
      },
      {
        onSuccess: (data) => setResult(data),
      }
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('stockHub.analysis')}</h1>

      {/* 配置区域 */}
      <div className="rounded-lg border p-4 space-y-4">
        {/* 回测数据源 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium">{t('stockHub.backtestSource')}</label>
            <select
              value={backtestName}
              onChange={(e) => { setBacktestName(e.target.value); setSelectedFactor('') }}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              <option value="">{t('stockHub.defaultSource')}</option>
              {backtests.map((bt) => (
                <option key={bt.name} value={bt.name}>
                  {bt.name} ({bt.factor_count}{t('stockHub.factorUnit')})
                </option>
              ))}
            </select>
          </div>

          {/* 因子选择 */}
          <div>
            <label className="text-sm font-medium">{t('stockHub.selectFactor')}</label>
            <select
              value={selectedFactor}
              onChange={(e) => setSelectedFactor(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              <option value="">{t('stockHub.pleaseSelect')}</option>
              {factors.map((f) => (
                <option key={f.name} value={f.name}>{f.display_name || f.name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 分析参数 */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="text-sm font-medium">{t('stockHub.periodPreset')}</label>
            <select
              value={periodPreset}
              onChange={(e) => setPeriodPreset(e.target.value as keyof typeof PERIOD_PRESETS)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              {Object.keys(PERIOD_PRESETS).map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">{t('stockHub.rebalanceTime')}</label>
            <select
              value={rebalanceTime}
              onChange={(e) => setRebalanceTime(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              {REBALANCE_TIMES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">{t('stockHub.groupCount')}</label>
            <input
              type="number"
              min={2}
              max={20}
              value={bins}
              onChange={(e) => setBins(Number(e.target.value))}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
            />
          </div>
        </div>

        {/* 执行按钮 */}
        <button
          onClick={handleAnalysis}
          disabled={!selectedFactor || analysisMutation.isPending}
          className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {analysisMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {t('stockHub.startAnalysis')}
        </button>

        {analysisMutation.isError && (
          <p className="text-sm text-destructive">{analysisMutation.error.message}</p>
        )}
      </div>

      {/* 结果展示 */}
      {result && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">{t('stockHub.analysisResult')}</h2>

          {/* 核心指标 */}
          <div className="grid grid-cols-5 gap-3">
            {[
              { label: 'IC', value: result.ic_mean.toFixed(4) },
              { label: 'ICIR', value: result.icir.toFixed(4) },
              { label: '|ICIR|', value: result.abs_icir.toFixed(4) },
              { label: t('stockHub.icWinRate'), value: result.ic_ratio },
              { label: t('stockHub.factorScore'), value: result.score.toFixed(4) },
            ].map((item) => (
              <div key={item.label} className="rounded-lg border p-3 text-center">
                <div className="text-xs text-muted-foreground">{item.label}</div>
                <div className="mt-1 text-lg font-bold">{item.value}</div>
              </div>
            ))}
          </div>

          {/* 分组收益 */}
          {Object.keys(result.group_values).length > 0 && (
            <div className="rounded-lg border p-4">
              <h3 className="mb-2 text-sm font-medium">{t('stockHub.groupReturns')}</h3>
              <div className="flex gap-1">
                {Object.entries(result.group_values).map(([group, val]) => (
                  <div
                    key={group}
                    className="flex-1 rounded bg-muted p-2 text-center text-xs"
                  >
                    <div className="text-muted-foreground">{group}</div>
                    <div className="font-mono">{val.toFixed(3)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 风格暴露 */}
          {Object.keys(result.style_exposure).length > 0 && (
            <div className="rounded-lg border p-4">
              <h3 className="mb-2 text-sm font-medium">{t('stockHub.styleExposure')}</h3>
              <div className="grid grid-cols-4 gap-2">
                {Object.entries(result.style_exposure).map(([style, val]) => (
                  <div key={style} className="flex items-center justify-between rounded bg-muted p-2 text-xs">
                    <span>{style}</span>
                    <span className="font-mono">{val.toFixed(3)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            {t('stockHub.elapsed', { seconds: result.elapsed_seconds })}
          </p>
        </div>
      )}
    </div>
  )
}
