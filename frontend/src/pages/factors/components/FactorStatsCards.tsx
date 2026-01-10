/**
 * Factor Stats Cards Component
 * 因子统计卡片组件
 */

import { FlaskConical, BarChart3, CheckCircle, XCircle } from 'lucide-react'
import type { FactorStats } from '@/features/factor'
import type { PipelineStatus } from '@/features/factor/pipeline-api'
import { StatsCard } from '@/features/factor/components/StatsCard'

// 字段顺序
const FIELD_ORDER = ['style', 'formula', 'input_data', 'value_range', 'description', 'analysis', 'llm_score']

interface FactorStatsCardsProps {
  stats?: FactorStats
  statsLoading: boolean
  pipelineStatus?: PipelineStatus
}

export function FactorStatsCards({ stats, statsLoading, pipelineStatus }: FactorStatsCardsProps) {
  // 计算平均填充率
  const avgFillRate = (() => {
    if (!pipelineStatus?.field_coverage) return '-'
    let totalFilled = 0
    let totalCount = 0
    FIELD_ORDER.forEach((field) => {
      const coverage = pipelineStatus.field_coverage[field]
      totalFilled += coverage?.filled ?? 0
      totalCount += (coverage?.filled ?? 0) + (coverage?.empty ?? 0)
    })
    return totalCount > 0 ? `${Math.round((totalFilled / totalCount) * 100)}%` : '-'
  })()

  if (statsLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-24 rounded-lg border bg-card animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatsCard
        title="有效因子"
        value={stats?.total ?? 0}
        icon={<FlaskConical className="h-5 w-5" />}
      />
      <StatsCard
        title="平均填充率"
        value={avgFillRate}
        icon={<BarChart3 className="h-5 w-5" />}
      />
      <StatsCard
        title="已校验"
        value={stats?.verified ?? 0}
        icon={<CheckCircle className="h-5 w-5" />}
      />
      <StatsCard
        title="已排除"
        value={stats?.excluded ?? 0}
        icon={<XCircle className="h-5 w-5" />}
      />
    </div>
  )
}
