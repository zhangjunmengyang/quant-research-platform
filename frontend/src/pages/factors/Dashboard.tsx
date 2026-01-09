/**
 * Factor Dashboard Page
 * 因子概览页 - 展示统计信息和完整因子列表
 */

import { useState, useMemo } from 'react'
import {
  BarChart3,
  CheckCircle,
  FlaskConical,
  XCircle,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Check,
  X,
  RotateCcw,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useFactorStats, useFactors, useFactorStyles, useFactorStore } from '@/features/factor'
import { pipelineApi } from '@/features/factor/pipeline-api'
import { StatsCard } from '@/features/factor/components/StatsCard'
import { FactorFilters } from '@/features/factor/components/FactorFilters'
import { FactorDetailPanelWrapper } from '@/features/factor/components/FactorDetailPanel'
import { ResizableTable, type TableColumn } from '@/components/ui/ResizableTable'
import { ColumnSelector } from '@/components/ui/ColumnSelector'
import { cn, stripPyExtension } from '@/lib/utils'
import type { Factor } from '@/features/factor'
import { FACTOR_TYPE_LABELS, FACTOR_COLUMNS, type FactorType } from '@/features/factor/types'

// 字段标签映射
const FIELD_LABELS: Record<string, string> = {
  style: '风格分类',
  formula: '计算公式',
  input_data: '输入数据',
  value_range: '值域范围',
  description: '因子描述',
  analysis: '因子分析',
  llm_score: 'LLM评分',
}

// 字段顺序
const FIELD_ORDER = ['style', 'formula', 'input_data', 'value_range', 'description', 'analysis', 'llm_score']

export function Component() {
  const { data: stats, isLoading: statsLoading } = useFactorStats()
  const { data: styles = [] } = useFactorStyles()
  const {
    filters,
    setFilters,
    openDetailPanel,
    visibleColumns,
    setVisibleColumns,
    columnWidths,
    setColumnWidth,
    resetColumnConfig,
  } = useFactorStore()
  const [searchQuery, setSearchQuery] = useState('')

  const { data, isLoading: factorsLoading, isError, error } = useFactors(filters)

  // 获取 pipeline status 用于字段覆盖率
  const { data: pipelineStatus } = useQuery({
    queryKey: ['pipeline-status'],
    queryFn: pipelineApi.getStatus,
  })

  // Filter by search query (client-side)
  const filteredItems = useMemo(() => {
    if (!data?.items || !searchQuery) return data?.items || []
    const query = searchQuery.toLowerCase()
    return data.items.filter(
      (factor) =>
        factor.filename.toLowerCase().includes(query) ||
        factor.style?.toLowerCase().includes(query) ||
        factor.description?.toLowerCase().includes(query)
    )
  }, [data?.items, searchQuery])

  const handlePageChange = (page: number) => {
    setFilters({ page })
  }

  if (statsLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="有效因子"
          value={stats?.total ?? 0}
          icon={<FlaskConical className="h-5 w-5" />}
        />
        <StatsCard
          title="平均填充率"
          value={(() => {
            if (!pipelineStatus?.field_coverage) return '-'
            let totalFilled = 0
            let totalCount = 0
            FIELD_ORDER.forEach((field) => {
              const coverage = pipelineStatus.field_coverage[field]
              totalFilled += coverage?.filled ?? 0
              totalCount += (coverage?.filled ?? 0) + (coverage?.empty ?? 0)
            })
            return totalCount > 0 ? `${Math.round((totalFilled / totalCount) * 100)}%` : '-'
          })()}
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

      {/* Charts */}
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
                    <div key={label} className="flex items-center gap-3">
                      <span className="w-12 truncate text-sm text-muted-foreground">{label}</span>
                      <div className="flex-1 h-6 bg-muted rounded-md overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all"
                          style={{
                            width: `${Math.min((count / (stats.total || 1)) * 100, 100)}%`,
                          }}
                        />
                      </div>
                      <span className="w-12 text-right text-sm font-medium">{count}</span>
                    </div>
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
                  <div key={style} className="flex items-center gap-3">
                    <span className="w-20 truncate text-sm text-muted-foreground" title={style}>
                      {style}
                    </span>
                    <div className="flex-1 h-6 bg-muted rounded-md overflow-hidden">
                      <div
                        className="h-full bg-info transition-all"
                        style={{
                          width: `${Math.min(((count as number) / (stats.total || 1)) * 100, 100)}%`,
                        }}
                      />
                    </div>
                    <span className="w-12 text-right text-sm font-medium">{count as number}</span>
                  </div>
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
                    <span className="w-16 truncate text-sm text-muted-foreground" title={FIELD_LABELS[field]}>
                      {FIELD_LABELS[field]}
                    </span>
                    <div className="flex-1 h-6 bg-muted rounded-md overflow-hidden">
                      <div
                        className="h-full bg-success transition-all"
                        style={{ width: `${rate}%` }}
                      />
                    </div>
                    <span className="w-16 text-right text-sm font-medium">{rate.toFixed(0)}%</span>
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

      {/* Factor Library Section */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">因子库</h2>

        {/* Filters */}
        <FactorFilters onSearch={setSearchQuery} searchValue={searchQuery} />

        {/* Toolbar */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            共 {data?.total ?? 0} 个因子
            {searchQuery && ` (筛选后 ${filteredItems.length} 个)`}
          </p>
          <div className="flex items-center gap-2">
            <ColumnSelector
              columns={FACTOR_COLUMNS.map((col) => ({
                key: col.key,
                label: col.label,
                required: col.key === 'filename', // 文件名必选
              }))}
              visibleColumns={visibleColumns}
              onChange={setVisibleColumns}
            />
            <button
              onClick={resetColumnConfig}
              className="rounded-md p-2 hover:bg-accent"
              title="重置列配置"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        {isError ? (
          <div className="flex h-64 flex-col items-center justify-center gap-4">
            <p className="text-destructive">加载失败: {(error as Error)?.message}</p>
            <button
              onClick={() => window.location.reload()}
              className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground"
            >
              重试
            </button>
          </div>
        ) : factorsLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <FactorTable
            factors={filteredItems}
            onSelect={openDetailPanel}
            visibleColumns={visibleColumns}
            columnWidths={columnWidths}
            onColumnWidthChange={setColumnWidth}
          />
        )}

        {/* Pagination */}
        {data && data.total > 0 && (
          <Pagination
            page={data.page}
            pageSize={data.page_size}
            total={data.total}
            totalPages={data.total_pages}
            onPageChange={handlePageChange}
            onPageSizeChange={(size) => setFilters({ page_size: size, page: 1 })}
          />
        )}
      </div>

      {/* Detail Panel */}
      <FactorDetailPanelWrapper />
    </div>
  )
}

/**
 * Factor Table View - 使用 ResizableTable 组件
 */
function FactorTable({
  factors,
  onSelect,
  visibleColumns,
  columnWidths,
  onColumnWidthChange,
}: {
  factors: Factor[]
  onSelect: (factor: Factor) => void
  visibleColumns: string[]
  columnWidths: Record<string, number>
  onColumnWidthChange: (columnKey: string, width: number) => void
}) {
  // 构建表格列配置
  const tableColumns = useMemo<TableColumn<Factor>[]>(() => {
    return visibleColumns
      .map((key) => {
        const colDef = FACTOR_COLUMNS.find((c) => c.key === key)
        if (!colDef) return null

        const column: TableColumn<Factor> = {
          key: colDef.key,
          label: colDef.label,
          width: columnWidths[colDef.key] ?? colDef.width ?? 100,
          minWidth: 50,
          maxWidth: 500,
        }

        // 根据列类型配置渲染函数
        switch (key) {
          case 'filename':
            column.render = (value) => (
              <span className="font-medium">{stripPyExtension(value as string)}</span>
            )
            break

          case 'factor_type':
            column.align = 'center'
            column.render = (value) => (
              <span
                className={cn(
                  'rounded-full px-2 py-1 text-xs font-medium',
                  value === 'cross_section'
                    ? 'bg-warning-muted text-warning'
                    : 'bg-info-muted text-info'
                )}
              >
                {FACTOR_TYPE_LABELS[value as FactorType] || '时序'}
              </span>
            )
            break

          case 'style':
            column.render = (value) => {
              if (!value) return null
              const styles = (value as string).split(',').filter(s => s.trim())
              return (
                <div className="flex flex-wrap gap-1">
                  {styles.map((style, i) => (
                    <span
                      key={i}
                      className="rounded-full bg-primary-muted px-2 py-0.5 text-xs font-medium text-primary"
                    >
                      {style.trim()}
                    </span>
                  ))}
                </div>
              )
            }
            break

          case 'tags':
            column.render = (value) => {
              if (!value) return null
              const tags = (value as string).split(',').slice(0, 3) // 最多显示3个标签
              return (
                <div className="flex flex-wrap gap-1">
                  {tags.map((tag, i) => (
                    <span
                      key={i}
                      className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground"
                    >
                      {tag.trim()}
                    </span>
                  ))}
                  {(value as string).split(',').length > 3 && (
                    <span className="text-xs text-muted-foreground">...</span>
                  )}
                </div>
              )
            }
            break

          case 'llm_score':
            column.align = 'center'
            column.render = (value) => {
              if (value === null || value === undefined) {
                return <span className="text-muted-foreground">-</span>
              }
              const score = value as number
              return (
                <span
                  className={cn(
                    'rounded-full px-2 py-1 text-xs font-medium',
                    score >= 4
                      ? 'bg-success-muted text-success'
                      : score >= 3
                        ? 'bg-warning-muted text-warning'
                        : 'bg-destructive-muted text-destructive'
                  )}
                >
                  {score}
                </span>
              )
            }
            break

          case 'verified':
            column.align = 'center'
            column.render = (value) => (
              <div className="flex items-center justify-center">
                {value ? (
                  <Check className="h-4 w-4 text-success" />
                ) : (
                  <X className="h-4 w-4 text-muted-foreground/50" />
                )}
              </div>
            )
            break

          case 'ic':
          case 'rank_ic':
            column.align = 'center'
            column.render = (value) => {
              if (value === null || value === undefined) {
                return <span className="text-muted-foreground">-</span>
              }
              return <span className="font-mono text-sm">{(value as number).toFixed(4)}</span>
            }
            break

          case 'created_at':
          case 'updated_at':
            column.render = (value) => {
              if (!value) return <span className="text-muted-foreground">-</span>
              const date = new Date(value as string)
              return (
                <span className="text-sm text-muted-foreground">
                  {date.toLocaleDateString('zh-CN')}
                </span>
              )
            }
            break

          // formula, input_data, value_range, description 等文本字段默认截断显示
          default:
            column.render = (value) => {
              if (!value) return <span className="text-muted-foreground">-</span>
              return <span className="text-sm">{value as string}</span>
            }
        }

        return column
      })
      .filter(Boolean) as TableColumn<Factor>[]
  }, [visibleColumns, columnWidths])

  if (factors.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center rounded-lg border text-muted-foreground">
        暂无因子
      </div>
    )
  }

  return (
    <ResizableTable
      columns={tableColumns}
      data={factors}
      rowKey="filename"
      onRowClick={onSelect}
      onColumnWidthChange={onColumnWidthChange}
      emptyText="暂无因子"
    />
  )
}

/**
 * Pagination Component
 */
function Pagination({
  page,
  pageSize,
  total,
  totalPages,
  onPageChange,
  onPageSizeChange,
}: {
  page: number
  pageSize: number
  total: number
  totalPages: number
  onPageChange: (page: number) => void
  onPageSizeChange: (size: number) => void
}) {
  return (
    <div className="flex items-center justify-end gap-3 text-sm">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="p-1.5 rounded hover:bg-accent disabled:opacity-30"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>
      <span className="text-muted-foreground">{page} / {totalPages}</span>
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        className="p-1.5 rounded hover:bg-accent disabled:opacity-30"
      >
        <ChevronRight className="h-4 w-4" />
      </button>

      <select
        value={pageSize}
        onChange={(e) => onPageSizeChange(Number(e.target.value))}
        className="h-8 px-2 rounded border bg-background text-sm"
      >
        <option value={20}>20条/页</option>
        <option value={50}>50条/页</option>
        <option value={100}>100条/页</option>
        <option value={200}>200条/页</option>
      </select>

      <span className="text-muted-foreground">
        共 {total} 条
      </span>
    </div>
  )
}
