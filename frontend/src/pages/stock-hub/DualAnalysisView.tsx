/**
 * Stock Hub - 双因子分析页
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Play } from 'lucide-react'
import {
  useStockStatus,
  useAvailableBacktests,
  useCachedFactors,
  useDualAnalysis,
  PERIOD_PRESETS,
  REBALANCE_TIMES,
} from '@/features/stock-hub'
import type { DualAnalysisResult } from '@/features/stock-hub'

export function Component() {
  const { t } = useTranslation()
  const { data: status, isLoading: statusLoading } = useStockStatus()
  const { data: backtestsData } = useAvailableBacktests()

  const [backtestName, setBacktestName] = useState('')
  const [mainFactor, setMainFactor] = useState('')
  const [subFactor, setSubFactor] = useState('')
  const [periodPreset, setPeriodPreset] = useState<keyof typeof PERIOD_PRESETS>('5日单offset')
  const [rebalanceTime, setRebalanceTime] = useState('0955')
  const [bins, setBins] = useState(5)
  const [result, setResult] = useState<DualAnalysisResult | null>(null)

  const { data: cachedFactors } = useCachedFactors(backtestName || undefined)
  const dualMutation = useDualAnalysis()

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
    if (!mainFactor || !subFactor || mainFactor === subFactor) return
    dualMutation.mutate(
      {
        main_factor: mainFactor,
        sub_factor: subFactor,
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
      <h1 className="text-2xl font-bold">{t('stockHub.dualAnalysis')}</h1>

      {/* 配置区域 */}
      <div className="rounded-lg border p-4 space-y-4">
        {/* 数据源 */}
        <div>
          <label className="text-sm font-medium">{t('stockHub.backtestSource')}</label>
          <select
            value={backtestName}
            onChange={(e) => { setBacktestName(e.target.value); setMainFactor(''); setSubFactor('') }}
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

        {/* 主次因子 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium">{t('stockHub.mainFactor')}</label>
            <select
              value={mainFactor}
              onChange={(e) => setMainFactor(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              <option value="">{t('stockHub.pleaseSelect')}</option>
              {factors.map((f) => (
                <option key={f.name} value={f.name}>{f.display_name || f.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">{t('stockHub.subFactor')}</label>
            <select
              value={subFactor}
              onChange={(e) => setSubFactor(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              <option value="">{t('stockHub.pleaseSelect')}</option>
              {factors.filter((f) => f.name !== mainFactor).map((f) => (
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

        {/* 验证提示 */}
        {mainFactor && subFactor && mainFactor === subFactor && (
          <p className="text-sm text-destructive">{t('stockHub.sameFactor')}</p>
        )}

        {/* 执行按钮 */}
        <button
          onClick={handleAnalysis}
          disabled={!mainFactor || !subFactor || mainFactor === subFactor || dualMutation.isPending}
          className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {dualMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {t('stockHub.startAnalysis')}
        </button>

        {dualMutation.isError && (
          <p className="text-sm text-destructive">{dualMutation.error.message}</p>
        )}
      </div>

      {/* 结果 */}
      {result && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">
            {t('stockHub.dualResult', { main: result.main_factor, sub: result.sub_factor })}
          </h2>
          <p className="text-xs text-muted-foreground">
            {t('stockHub.elapsed', { seconds: result.elapsed_seconds })}
          </p>
        </div>
      )}
    </div>
  )
}
