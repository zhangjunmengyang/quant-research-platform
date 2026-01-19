/**
 * Factor Dashboard Page
 * 因子概览页 - 展示统计信息和完整因子列表
 */

import { useState, useMemo, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Loader2, RotateCcw, Check, X } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import {
  useFactorStats,
  useFactors,
  useFactorStore,
  DEFAULT_FACTOR_FILTERS,
} from '@/features/factor'
import type { FactorListParams } from '@/features/factor/types'
import { pipelineApi } from '@/features/factor/pipeline-api'
import { FactorFilters } from '@/features/factor/components/FactorFilters'
import { FactorDetailPanelWrapper } from '@/features/factor/components/FactorDetailPanel'
import { ResizableTable, type TableColumn } from '@/components/ui/ResizableTable'
import { ColumnSelector } from '@/components/ui/ColumnSelector'
import { Pagination } from '@/components/ui/pagination'
import { cn, stripPyExtension } from '@/lib/utils'
import type { Factor } from '@/features/factor'
import {
  FACTOR_TYPE_LABELS,
  FACTOR_COLUMNS,
  type FactorType,
} from '@/features/factor/types'
import { paramsToFactorFilters, factorFiltersToParams } from '@/lib/url-params'
import { FactorStatsCards } from './components/FactorStatsCards'
import { FactorCharts } from './components/FactorCharts'

export function Component() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { data: stats, isLoading: statsLoading, isError: statsError } = useFactorStats()
  const {
    openDetailPanel,
    visibleColumns,
    setVisibleColumns,
    columnWidths,
    setColumnWidth,
    resetColumnConfig,
  } = useFactorStore()
  const [searchQuery, setSearchQuery] = useState('')

  // 从 URL 读取 filters
  const filters = useMemo(
    () => paramsToFactorFilters(searchParams),
    [searchParams]
  )

  // 更新 filters 并同步到 URL
  const setFilters = useCallback(
    (newFilters: Partial<FactorListParams>) => {
      const updatedFilters = { ...filters, ...newFilters }
      const params = factorFiltersToParams(updatedFilters)
      // 移除空值参数
      Object.keys(params).forEach((key) => {
        if (params[key] === '' || params[key] === 'undefined') {
          delete params[key]
        }
      })
      setSearchParams(params)
    },
    [filters, setSearchParams]
  )

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

  // 重置 filters 到默认值
  const resetFilters = useCallback(() => {
    const params = factorFiltersToParams(DEFAULT_FACTOR_FILTERS)
    setSearchParams(params)
  }, [setSearchParams])

  if (statsLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (statsError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <p className="text-destructive">加载统计数据失败</p>
        <button
          onClick={() => window.location.reload()}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground"
        >
          重试
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Metrics Cards */}
      <FactorStatsCards
        stats={stats}
        statsLoading={statsLoading}
        pipelineStatus={pipelineStatus}
      />

      {/* Charts */}
      <FactorCharts stats={stats} pipelineStatus={pipelineStatus} />

      {/* Factor Library Section */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">因子库</h2>

        {/* Filters */}
        <FactorFilters
          filters={filters}
          setFilters={setFilters}
          resetFilters={resetFilters}
          onSearch={setSearchQuery}
          searchValue={searchQuery}
        />

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
interface FactorTableProps {
  factors: Factor[]
  onSelect: (factor: Factor) => void
  visibleColumns: string[]
  columnWidths: Record<string, number>
  onColumnWidthChange: (columnKey: string, width: number) => void
}

function FactorTable({
  factors,
  onSelect,
  visibleColumns,
  columnWidths,
  onColumnWidthChange,
}: FactorTableProps) {
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
              const styles = (value as string).split(',').filter((s) => s.trim())
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
