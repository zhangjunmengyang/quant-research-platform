/**
 * AI因子评估浏览页 — 查看所有因子的AI评估结果
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Sparkles, ChevronDown, ChevronUp, Clock } from 'lucide-react'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

import {
  useStockEvaluations,
  useStockEvaluation,
  useStockHubStatus,
} from '@/features/stock-hub'
import type { EvaluationListItem } from '@/features/stock-hub'
import { StockHubNotConfigured } from './StockHubNotConfigured'

// ===== Score helpers =====

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

function verdictVariant(verdict: string): 'success' | 'warning' | 'destructive' {
  if (verdict === '\u63a8\u8350') return 'success'
  if (verdict === '\u5f03\u7528') return 'destructive'
  return 'warning'
}

function verdictLabel(verdict: string, t: (key: string) => string): string {
  if (verdict === '\u63a8\u8350') return t('stockHub.verdictRecommend')
  if (verdict === '\u5f03\u7528') return t('stockHub.verdictReject')
  return t('stockHub.verdictWatch')
}

function formatDate(ts: number): string {
  return new Date(ts * 1000).toLocaleString()
}

// ===== Module Score Card =====

function ModuleScoreCard({
  label,
  score,
  analysis,
}: {
  label: string
  score: number
  analysis: string
}) {
  return (
    <div className="rounded-lg border p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
        <span className={`text-lg font-bold ${scoreColor(score)}`}>
          {score.toFixed(1)}
        </span>
      </div>
      <p className="text-sm leading-relaxed">{analysis}</p>
    </div>
  )
}

// ===== Expanded Detail =====

function EvaluationDetail({ factorName }: { factorName: string }) {
  const { t } = useTranslation()
  const { data: evaluation, isLoading } = useStockEvaluation(factorName)

  if (isLoading) {
    return (
      <div className="py-4 text-center text-sm text-muted-foreground">
        {t('common.loading')}
      </div>
    )
  }

  if (!evaluation) return null

  return (
    <div className="space-y-3 pt-3 border-t">
      {/* Module scores */}
      <div className="grid gap-3 md:grid-cols-3">
        {evaluation.logic && (
          <ModuleScoreCard
            label={t('stockHub.logicScore')}
            score={evaluation.logic.score}
            analysis={evaluation.logic.analysis}
          />
        )}
        {evaluation.backtest && (
          <ModuleScoreCard
            label={t('stockHub.backtestScore')}
            score={evaluation.backtest.score}
            analysis={evaluation.backtest.analysis}
          />
        )}
        {evaluation.effectiveness && (
          <ModuleScoreCard
            label={t('stockHub.icScore')}
            score={evaluation.effectiveness.score}
            analysis={evaluation.effectiveness.analysis}
          />
        )}
      </div>

      {/* Overall summary */}
      {evaluation.overall_summary && (
        <div className="rounded-lg border p-3 space-y-2">
          <span className="text-sm font-medium text-muted-foreground">
            {t('stockHub.overallScore')}
          </span>
          <p className="text-sm leading-relaxed">{evaluation.overall_summary}</p>
        </div>
      )}
    </div>
  )
}

// ===== Single Evaluation Card =====

function EvaluationCard({ item }: { item: EvaluationListItem }) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)

  return (
    <Card>
      <CardContent className="p-4">
        {/* Header row */}
        <button
          type="button"
          className="flex w-full items-center gap-3 text-left"
          onClick={() => setExpanded(!expanded)}
        >
          {/* Score circle */}
          <div
            className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full ${scoreBg(item.overall_score)}`}
          >
            <span className={`text-lg font-bold ${scoreColor(item.overall_score)}`}>
              {item.overall_score !== null ? item.overall_score.toFixed(1) : '-'}
            </span>
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium truncate">{item.factor_name}</span>
              {item.factor_category && (
                <Badge variant="secondary" className="text-xs">
                  {item.factor_category}
                </Badge>
              )}
              {item.verdict && (
                <Badge variant={verdictVariant(item.verdict)} className="text-xs">
                  {verdictLabel(item.verdict, t)}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1">
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                {formatDate(item.evaluated_at)}
              </span>
              {item.tags.length > 0 && (
                <div className="flex gap-1">
                  {item.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Expand icon */}
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          )}
        </button>

        {/* Expanded detail */}
        {expanded && <EvaluationDetail factorName={item.factor_name} />}
      </CardContent>
    </Card>
  )
}

// ===== Main Page =====

export function Component() {
  const { t } = useTranslation()
  const { data: status } = useStockHubStatus()
  const { data, isLoading } = useStockEvaluations()

  if (status && !status.available) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{t('stockHub.evaluation')}</h1>
        <StockHubNotConfigured status={status} />
      </div>
    )
  }

  const evaluations = data?.evaluations ?? []

  return (
    <div className="space-y-4">
      {/* Title */}
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-primary" />
        <h1 className="text-2xl font-bold">{t('stockHub.evaluation')}</h1>
        {evaluations.length > 0 && (
          <Badge variant="secondary">{evaluations.length}</Badge>
        )}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="py-12 text-center text-muted-foreground">
          {t('common.loading')}
        </div>
      ) : evaluations.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Sparkles className="mx-auto h-8 w-8 mb-3 opacity-50" />
            <p>{t('stockHub.noEvaluations')}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {evaluations.map((item) => (
            <EvaluationCard key={item.factor_name} item={item} />
          ))}
        </div>
      )}
    </div>
  )
}
