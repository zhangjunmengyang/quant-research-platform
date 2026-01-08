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
  ExperienceFilters,
  ExperienceDetailPanelWrapper,
  ExperienceCreateDialog,
} from '@/features/experience'
import type { ExperienceListParams } from '@/features/experience'
import { cn } from '@/lib/utils'

// 统计卡片组件
function StatsCard({
  title,
  value,
  icon: Icon,
  description,
  colorClass,
}: {
  title: string
  value: number | string
  icon: React.ComponentType<{ className?: string }>
  description?: string
  colorClass?: string
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center gap-3">
        <div className={cn('rounded-lg p-2', colorClass || 'bg-primary/10')}>
          <Icon className={cn('h-5 w-5', colorClass ? 'text-white' : 'text-primary')} />
        </div>
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-sm text-muted-foreground">{title}</p>
          {description && <p className="text-xs text-muted-foreground">{description}</p>}
        </div>
      </div>
    </div>
  )
}

export function Component() {
  const { filters, setFilters, openDetailPanel } = useExperienceStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)

  // 防抖搜索
  const debouncedSearch = useDebounce(searchQuery, 300)

  // 构建查询参数
  const queryParams: ExperienceListParams = useMemo(
    () => ({
      ...filters,
      // 搜索功能可以通过后端支持或前端过滤实现
    }),
    [filters]
  )

  // 获取数据
  const { data, isLoading, isError, error } = useExperiences(queryParams)
  const { data: stats } = useExperienceStats()

  // 处理搜索
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query)
  }, [])

  // 处理分页
  const handlePageChange = useCallback(
    (page: number) => {
      setFilters({ page })
    },
    [setFilters]
  )

  // 处理创建成功
  const handleCreateSuccess = useCallback(() => {
    // 可以添加 toast 提示
  }, [])

  // 过滤搜索结果（前端过滤）
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
          <StatsCard title="总经验" value={stats.total} icon={BarChart3} />
          <StatsCard
            title="战略级"
            value={stats.by_level?.strategic || 0}
            icon={Target}
            colorClass="bg-purple-500"
          />
          <StatsCard
            title="战术级"
            value={stats.by_level?.tactical || 0}
            icon={Lightbulb}
            colorClass="bg-blue-500"
          />
          <StatsCard
            title="已验证"
            value={stats.by_status?.validated || 0}
            icon={CheckCircle2}
            colorClass="bg-green-500"
          />
        </div>
      )}

      {/* Filters */}
      <ExperienceFilters onSearch={handleSearch} searchValue={searchQuery} />

      {/* Experience List */}
      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="flex h-48 flex-col items-center justify-center rounded-lg border border-dashed">
          <FileText className="h-12 w-12 text-muted-foreground/50" />
          <p className="mt-4 text-muted-foreground">
            {debouncedSearch ? '没有匹配的经验' : '还没有经验记录'}
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
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => handlePageChange((filters.page ?? 1) - 1)}
            disabled={!data.has_prev}
            className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
          >
            上一页
          </button>
          <span className="text-sm text-muted-foreground">
            第 {data.page} / {data.total_pages} 页
          </span>
          <button
            onClick={() => handlePageChange((filters.page ?? 1) + 1)}
            disabled={!data.has_next}
            className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
          >
            下一页
          </button>
        </div>
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
