/**
 * A股回测面板 — 配置策略、提交回测、查看历史
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Play, Clock, Trash2, Plus, ChevronRight, AlertCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge, StatusBadge } from '@/components/ui/badge'

import {
  useSubmitBacktest,
  useStockBacktests,
  useStockHubStore,
  useStockHubStatus,
} from '@/features/stock-hub'
import type {
  StockBacktestRequest,
  StockStrategyConfig,
  StockFactorConfig,
} from '@/features/stock-hub'
import { StockHubNotConfigured } from './StockHubNotConfigured'

// ===== 因子选择行 =====

function FactorRow({
  factor,
  onChange,
  onRemove,
}: {
  factor: StockFactorConfig
  onChange: (f: StockFactorConfig) => void
  onRemove: () => void
}) {
  const { t } = useTranslation()
  return (
    <div className="flex items-center gap-2 text-sm">
      <input
        type="text"
        value={factor.name}
        onChange={(e) => onChange({ ...factor, name: e.target.value })}
        placeholder={t('stockHub.factorName')}
        className="h-8 w-40 rounded border border-input bg-background px-2 text-sm"
      />
      <select
        value={factor.ascending ? 'true' : 'false'}
        onChange={(e) => onChange({ ...factor, ascending: e.target.value === 'true' })}
        className="h-8 rounded border border-input bg-background px-2 text-sm"
      >
        <option value="true">{t('stockHub.ascending')}</option>
        <option value="false">{t('stockHub.descending')}</option>
      </select>
      <div className="relative">
        <input
          type="text"
          value={factor.param}
          onChange={(e) => onChange({ ...factor, param: e.target.value })}
          placeholder={t('stockHub.param')}
          className="h-8 w-20 rounded border border-input bg-background px-2 text-sm"
          title={t('stockHub.paramHint')}
        />
      </div>
      <input
        type="number"
        value={factor.weight}
        onChange={(e) => onChange({ ...factor, weight: Number(e.target.value) })}
        className="h-8 w-16 rounded border border-input bg-background px-2 text-sm"
        min={0}
        step={0.1}
        title={t('stockHub.weight')}
      />
      <Button variant="ghost" size="icon-sm" onClick={onRemove}>
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
}

// ===== 回测配置表单 =====

function BacktestConfigForm() {
  const { t } = useTranslation()
  const submitMutation = useSubmitBacktest()
  const { pendingFactors, clearPendingFactors } = useStockHubStore()

  const [config, setConfig] = useState({
    backtest_name: '',
    start_date: '2023-01-01',
    end_date: '',
    strategy_name: t('stockHub.defaultStrategyName'),
    hold_period: 'W',
    select_num: 3,
    factors: [] as StockFactorConfig[],
  })

  // 从 store 载入待回测因子
  useEffect(() => {
    if (pendingFactors.length > 0 && config.factors.length === 0) {
      setConfig((prev) => ({ ...prev, factors: [...pendingFactors] }))
    }
  }, [pendingFactors, config.factors.length])

  const [errors, setErrors] = useState<string[]>([])

  const validate = (): boolean => {
    const errs: string[] = []
    if (!config.backtest_name.trim()) errs.push(t('stockHub.validationNameRequired'))
    if (config.factors.every((f) => !f.name.trim())) errs.push(t('stockHub.validationFactorRequired'))
    if (config.end_date && config.start_date > config.end_date)
      errs.push(t('stockHub.validationDateRange'))
    setErrors(errs)
    return errs.length === 0
  }

  const addFactor = () => {
    setConfig((prev) => ({
      ...prev,
      factors: [...prev.factors, { name: '', ascending: true, param: '静态', weight: 1 }],
    }))
  }

  const removeFactor = (idx: number) => {
    setConfig((prev) => ({
      ...prev,
      factors: prev.factors.filter((_, i) => i !== idx),
    }))
  }

  const updateFactor = (idx: number, f: StockFactorConfig) => {
    setConfig((prev) => ({
      ...prev,
      factors: prev.factors.map((old, i) => (i === idx ? f : old)),
    }))
  }

  const handleSubmit = () => {
    if (!validate()) return

    const strategy: StockStrategyConfig = {
      name: config.strategy_name,
      hold_period: config.hold_period,
      offset_list: [1],
      select_num: config.select_num,
      cap_weight: 1,
      rebalance_time: '15:00',
      factor_list: config.factors.filter((f) => f.name.trim()),
      filter_list: [],
    }

    const request: StockBacktestRequest = {
      backtest_name: config.backtest_name,
      start_date: config.start_date,
      end_date: config.end_date || undefined,
      strategies: [strategy],
    }

    submitMutation.mutate(request, {
      onSuccess: () => {
        clearPendingFactors()
      },
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t('stockHub.backtestConfig')}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 验证错误 */}
        {errors.length > 0 && (
          <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 space-y-1">
            {errors.map((err) => (
              <p key={err} className="text-sm text-destructive flex items-center gap-1">
                <AlertCircle className="h-3.5 w-3.5" />
                {err}
              </p>
            ))}
          </div>
        )}

        {/* 回测名称 + 日期 */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              {t('stockHub.backtestName')} *
            </label>
            <input
              type="text"
              value={config.backtest_name}
              onChange={(e) => setConfig((p) => ({ ...p, backtest_name: e.target.value }))}
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              placeholder={t('stockHub.backtestNamePlaceholder')}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              {t('stockHub.startDate')}
            </label>
            <input
              type="date"
              value={config.start_date}
              onChange={(e) => setConfig((p) => ({ ...p, start_date: e.target.value }))}
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              {t('stockHub.endDate')}
            </label>
            <input
              type="date"
              value={config.end_date}
              onChange={(e) => setConfig((p) => ({ ...p, end_date: e.target.value }))}
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            />
          </div>
        </div>

        {/* 策略参数 */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              {t('stockHub.strategyName')}
            </label>
            <input
              type="text"
              value={config.strategy_name}
              onChange={(e) => setConfig((p) => ({ ...p, strategy_name: e.target.value }))}
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              {t('stockHub.holdPeriod')}
            </label>
            <select
              value={config.hold_period}
              onChange={(e) => setConfig((p) => ({ ...p, hold_period: e.target.value }))}
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="W">{t('stockHub.holdW')}</option>
              <option value="M">{t('stockHub.holdM')}</option>
              <option value="D">{t('stockHub.holdD')}</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              {t('stockHub.selectNum')}
            </label>
            <input
              type="number"
              value={config.select_num}
              onChange={(e) => setConfig((p) => ({ ...p, select_num: Number(e.target.value) }))}
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              min={1}
            />
          </div>
        </div>

        {/* 因子列表 */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <div>
              <label className="text-xs font-medium text-muted-foreground">
                {t('stockHub.addFactor')} *
              </label>
              <p className="text-2xs text-muted-foreground/70">{t('stockHub.paramHint')}</p>
            </div>
            <Button variant="outline" size="sm" onClick={addFactor} className="gap-1">
              <Plus className="h-3 w-3" />
              {t('stockHub.addFactor')}
            </Button>
          </div>
          {config.factors.length === 0 && (
            <p className="text-sm text-muted-foreground py-3 text-center border border-dashed rounded-md">
              {t('stockHub.validationFactorRequired')}
            </p>
          )}
          <div className="space-y-2">
            {config.factors.map((f, i) => (
              <FactorRow
                key={i}
                factor={f}
                onChange={(updated) => updateFactor(i, updated)}
                onRemove={() => removeFactor(i)}
              />
            ))}
          </div>
        </div>

        {/* 提交 */}
        <div className="flex items-center gap-3">
          <Button
            onClick={handleSubmit}
            loading={submitMutation.isPending}
            disabled={submitMutation.isPending}
            className="gap-1"
          >
            <Play className="h-4 w-4" />
            {submitMutation.isPending
              ? t('stockHub.backtestRunning')
              : t('stockHub.submitBacktest')}
          </Button>
          {submitMutation.isSuccess && submitMutation.data && (
            <Badge variant="success">
              {submitMutation.data.result?.status === 'ok'
                ? `${t('backtest.completed')} ✓`
                : submitMutation.data.result?.status}
            </Badge>
          )}
          {submitMutation.isError && (
            <Badge variant="destructive">
              {(submitMutation.error as Error).message}
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

// ===== 回测历史列表 =====

function BacktestHistory() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data } = useStockBacktests()
  const tasks = data?.tasks ?? []

  if (tasks.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          {t('stockHub.noBacktestTasks')}
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Clock className="h-4 w-4" />
          {t('stockHub.backtestHistory')}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 p-3">
        {tasks.map((task) => (
          <div
            key={task.task_id}
            className="flex items-center justify-between rounded-md border p-3 hover:bg-muted/50 cursor-pointer"
            onClick={() => {
              if (task.result?.result_path) {
                navigate(
                  `/stock-hub/analysis?task_id=${task.task_id}`
                )
              }
            }}
          >
            <div className="flex items-center gap-3">
              <StatusBadge
                status={
                  task.status === 'ok' || task.status === 'completed'
                    ? 'success'
                    : task.status === 'running'
                      ? 'pending'
                      : 'error'
                }
                label={task.status}
              />
              <div>
                <p className="text-sm font-medium">
                  {task.backtest_name || task.task_id}
                </p>
                <p className="text-xs text-muted-foreground">
                  {new Date(task.submitted_at * 1000).toLocaleString()}
                  {task.result?.result_path && (
                    <span className="ml-2 text-green-600 dark:text-green-400">
                      {t('backtest.completed')}
                    </span>
                  )}
                </p>
              </div>
            </div>
            {task.result?.result_path && (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

// ===== 主页面 =====

export function Component() {
  const { t } = useTranslation()
  const { backtestTab, setBacktestTab } = useStockHubStore()
  const { data: status } = useStockHubStatus()

  if (status && !status.available) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{t('stockHub.backtest')}</h1>
        <StockHubNotConfigured status={status} />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t('stockHub.backtest')}</h1>

      {/* Tab 切换 */}
      <div className="flex gap-1 border-b">
        {(['config', 'history'] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setBacktestTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              backtestTab === tab
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab === 'config' ? t('stockHub.backtestConfig') : t('stockHub.backtestHistory')}
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      {backtestTab === 'config' ? <BacktestConfigForm /> : <BacktestHistory />}
    </div>
  )
}
