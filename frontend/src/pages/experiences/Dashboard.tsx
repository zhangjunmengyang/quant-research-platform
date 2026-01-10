/**
 * Experiences Dashboard Page
 *
 * 经验知识库仪表盘 - 展示经验列表和统计信息
 */

import { useState, useCallback, useMemo } from 'react'
import { useDebounce } from '@/hooks/useDebounce'
import { Loader2, Plus, BarChart3, Target, Lightbulb, FileText, CheckCircle2 } from 'lucide-react'
import {
  useExperiences,
  useExperienceStats,
  useExperienceStore,
  ExperienceCard,
  ExperienceDetailPanelWrapper,
  ExperienceCreateDialog,
} from '@/features/experience'
import { ExperienceFilters } from '@/features/experience/components/ExperienceFilters'
import type { ExperienceListParams } from '@/features/experience'
import { StatsCard } from '@/features/factor/components/StatsCard'
import { Pagination } from '@/components/ui/pagination'

const DEFAULT_FILTERS: Partial<ExperienceListParams> = {
  page: 1,
  page_size: 20,
  order_by: 'updated_at',
  order_desc: true,
}

export function Component() {
  // UI 状态（保留在 store 中）
  const { openDetailPanel } = useExperienceStore()
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)

  // 筛选状态使用组件 state 管理
  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState<Partial<ExperienceListParams>>(DEFAULT_FILTERS)

  // 防抖搜索
  const debouncedSearch = useDebounce(searchQuery, 300)

  // 构建查询参数
  const queryParams: ExperienceListParams = useMemo(
    () => ({
      ...filters,
      search: debouncedSearch || undefined,
    }),
    [filters, debouncedSearch]
  )

  // 获取数据
  const { data, isLoading, isError, error } = useExperiences(queryParams)
  const { data: stats } = useExperienceStats()

  // 处理搜索
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query)
    setFilters((prev) => ({ ...prev, page: 1 }))
  }, [])

  // 处理筛选变更
  const handleFilterChange = useCallback((newFilters: Partial<ExperienceListParams>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }))
  }, [])

  // 处理重置筛选
  const handleResetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS)
    setSearchQuery('')
    setSearchInput('')
  }, [])

  // 处理分页
  const handlePageChange = useCallback((page: number) => {
    setFilters((prev) => ({ ...prev, page }))
  }, [])

  // 处理创建成功
  const handleCreateSuccess = useCallback(() => {
    // 可以添加 toast 提示
  }, [])

  // 检查是否有活跃筛选
  const hasActiveFilters = useMemo(() => {
    return !!(
      searchQuery ||
      filters.experience_level ||
      filters.status ||
      filters.category ||
      filters.source_type ||
      filters.market_regime
    )
  }, [searchQuery, filters])

  // 过滤搜索结果（前端过滤，待后端支持搜索后可移除）
  const filteredItems = useMemo(() => {
    if (!data?.items) return []
    if (!debouncedSearch) return data.items

    const query = debouncedSearch.toLowerCase()
    return data.items.filter(
      (exp) =>
        exp.title.toLowerCase().includes(query) ||
        exp.content?.lesson?.toLowerCase().includes(query) ||
        exp.content?.problem?.toLowerCase().includes(query) ||
        exp.context?.tags?.some((tag) => tag.toLowerCase().includes(query))
    )
  }, [data?.items, debouncedSearch])

  if (isError) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-destructive">
        <p>加载失败</p>
        <p className="text-sm">{(error as Error)?.message}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">经验知识库</h1>
          <p className="text-muted-foreground">
            记录和管理研究过程中的经验与教训
          </p>
        </div>
        <button
          onClick={() => setIsCreateDialogOpen(true)}
          className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          新建经验
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatsCard
            title="总经验"
            value={stats.total}
            icon={<BarChart3 className="h-5 w-5" />}
          />
          <StatsCard
            title="战略级"
            value={stats.by_level?.strategic || 0}
            icon={<Target className="h-5 w-5" />}
          />
          <StatsCard
            title="战术级"
            value={stats.by_level?.tactical || 0}
            icon={<Lightbulb className="h-5 w-5" />}
          />
          <StatsCard
            title="已验证"
            value={stats.by_status?.validated || 0}
            icon={<CheckCircle2 className="h-5 w-5" />}
          />
        </div>
      )}

      {/* Filters */}
      <ExperienceFilters
        filters={filters}
        setFilters={handleFilterChange}
        resetFilters={handleResetFilters}
        onSearch={handleSearch}
        searchValue={searchQuery}
        onSearchInputChange={(value) => setSearchInput(value)}
        searchInputValue={searchInput}
        hasActiveFilters={hasActiveFilters}
      />

      {/* Experience List */}
      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="flex h-48 flex-col items-center justify-center rounded-lg border border-dashed">
          <FileText className="h-12 w-12 text-muted-foreground/50" />
          <p className="mt-4 text-muted-foreground">
            {hasActiveFilters ? '没有匹配的经验' : '还没有经验记录'}
          </p>
          <button
            onClick={() => setIsCreateDialogOpen(true)}
            className="mt-4 flex items-center gap-2 text-sm text-primary hover:underline"
          >
            <Plus className="h-4 w-4" />
            创建第一条经验
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredItems.map((experience) => (
            <ExperienceCard
              key={experience.id}
              experience={experience}
              onClick={() => openDetailPanel(experience)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <Pagination
          page={data.page}
          pageSize={data.page_size}
          total={data.total}
          totalPages={data.total_pages}
          onPageChange={handlePageChange}
          position="center"
        />
      )}

      {/* Detail Panel */}
      <ExperienceDetailPanelWrapper />

      {/* Create Dialog */}
      <ExperienceCreateDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        onSuccess={handleCreateSuccess}
      />
    </div>
  )
}
