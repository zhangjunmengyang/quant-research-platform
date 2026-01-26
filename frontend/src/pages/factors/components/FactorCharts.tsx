/**
 * Factor Charts Component
 * 因子图表组件 - 包含评分分布、风格分布、字段填充率
 */

import type { FactorStats } from '@/features/factor'
import type { PipelineStatus } from '@/features/factor/pipeline-api'

// 字段标签映射 (与 FactorDetailPanel 保持一致)
const FIELD_LABELS: Record<string, string> = {
  style: '风格',
  formula: '公式',
  input_data: '输入数据',
  value_range: '值域',
  description: '刻画特征',
  analysis: '深度分析',
  llm_score: 'LLM评分',
}

// 字段顺序
const FIELD_ORDER = ['style', 'formula', 'input_data', 'value_range', 'description', 'analysis', 'llm_score']

interface ScoreBarProps {
  label: string
  count: number
  total: number
  color?: string
}

function ScoreBar({ label, count, total, color = 'bg-primary' }: ScoreBarProps) {
  const percentage = total > 0 ? Math.min((count / total) * 100, 100) : 0

  return (
    <div className="flex items-center gap-3">
      <span className="w-12 truncate text-sm text-muted-foreground">{label}</span>
      <div className="flex-1 h-6 bg-muted rounded-md overflow-hidden">
        <div
          className={`h-full ${color} transition-all`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="w-12 text-right text-sm font-medium">{count}</span>
    </div>
  )
}

interface FactorChartsProps {
  stats?: FactorStats
  pipelineStatus?: PipelineStatus
}

export function FactorCharts({ stats, pipelineStatus }: FactorChartsProps) {
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* Score Distribution */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 font-semibold">评分分布</h3>
        <div className="space-y-3">
          {stats?.score_distribution ? (
            // 显示所有评分区间（包括计数为0的）
            (() => {
              // 定义分数段：0-1.5 合并，其余每 0.5 分一档
              const scoreRanges: { label: string; keys: string[] }[] = [
                { label: '0-1.5', keys: ['0-0.5', '0.5-1', '1-1.5'] },
                { label: '1.5-2', keys: ['1.5-2'] },
                { label: '2-2.5', keys: ['2-2.5'] },
                { label: '2.5-3', keys: ['2.5-3'] },
                { label: '3-3.5', keys: ['3-3.5'] },
                { label: '3.5-4', keys: ['3.5-4'] },
                { label: '4-4.5', keys: ['4-4.5'] },
                { label: '4.5-5', keys: ['4.5-5'] },
              ]
              return scoreRanges.map(({ label, keys }) => {
                const count = keys.reduce(
                  (sum, key) => sum + ((stats.score_distribution[key] as number) || 0),
                  0
                )
                return (
                  <ScoreBar
                    key={label}
                    label={label}
                    count={count}
                    total={stats.total || 1}
                  />
                )
              })
            })()
          ) : (
            <div className="flex h-48 items-center justify-center text-muted-foreground">
              暂无评分数据
            </div>
          )}
        </div>
      </div>

      {/* Style Distribution */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 font-semibold">风格分布</h3>
        <div className="space-y-3">
          {stats?.style_distribution ? (
            Object.entries(stats.style_distribution)
              .sort(([, a], [, b]) => (b as number) - (a as number))
              .slice(0, 8)
              .map(([style, count]) => (
                <ScoreBar
                  key={style}
                  label={style}
                  count={count as number}
                  total={stats.total || 1}
                  color="bg-info"
                />
              ))
          ) : (
            <div className="flex h-48 items-center justify-center text-muted-foreground">
              暂无风格数据
            </div>
          )}
        </div>
      </div>

      {/* Field Coverage */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="mb-4 font-semibold">字段填充率</h3>
        <div className="space-y-3">
          {pipelineStatus?.field_coverage ? (
            FIELD_ORDER.map((field) => {
              const coverage = pipelineStatus.field_coverage[field]
              const filled = coverage?.filled ?? 0
              const empty = coverage?.empty ?? 0
              const total = filled + empty
              const rate = total > 0 ? (filled / total) * 100 : 0
              return (
                <div key={field} className="flex items-center gap-3">
                  <span
                    className="w-16 truncate text-sm text-muted-foreground"
                    title={FIELD_LABELS[field]}
                  >
                    {FIELD_LABELS[field]}
                  </span>
                  <div className="flex-1 h-6 bg-muted rounded-md overflow-hidden">
                    <div
                      className="h-full bg-success transition-all"
                      style={{ width: `${rate}%` }}
                    />
                  </div>
                  <span className="w-16 text-right text-sm font-medium">
                    {rate.toFixed(0)}%
                  </span>
                </div>
              )
            })
          ) : (
            <div className="flex h-48 items-center justify-center text-muted-foreground">
              暂无填充数据
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
