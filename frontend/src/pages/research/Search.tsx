/**
 * Research Semantic Search Page
 * 研报语义搜索页 - 向量检索研报内容
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  Loader2,
  FileText,
  Sparkles,
  ExternalLink,
  SlidersHorizontal,
} from 'lucide-react'
import { useSearch, useReports } from '@/features/research'
import type { SearchResultItem, SearchRequest } from '@/features/research'
import { cn } from '@/lib/utils'

export function Component() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(10)
  const [minScore, setMinScore] = useState(0)
  const [selectedReportId, setSelectedReportId] = useState<number | undefined>()
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [results, setResults] = useState<SearchResultItem[]>([])
  const [lastQuery, setLastQuery] = useState('')

  const searchMutation = useSearch()
  const { data: reportsData } = useReports({ page_size: 100, status: 'ready' })

  const handleSearch = async () => {
    if (!query.trim()) return

    const request: SearchRequest = {
      query: query.trim(),
      top_k: topK,
      min_score: minScore,
      report_id: selectedReportId,
    }

    try {
      const response = await searchMutation.mutateAsync(request)
      setResults(response.results)
      setLastQuery(query)
    } catch (err) {
      console.error('Search failed:', err)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600 bg-green-100'
    if (score >= 0.6) return 'text-yellow-600 bg-yellow-100'
    if (score >= 0.4) return 'text-orange-600 bg-orange-100'
    return 'text-gray-600 bg-gray-100'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Sparkles className="h-6 w-6" />
          语义搜索
        </h1>
        <p className="text-muted-foreground">
          使用向量相似度检索研报内容，找到语义相关的片段
        </p>
      </div>

      {/* Search Box */}
      <div className="space-y-4">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="输入搜索内容，例如：动量因子在牛市中的表现..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full rounded-lg border bg-background py-3 pl-11 pr-4 text-base focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={searchMutation.isPending || !query.trim()}
            className="flex items-center gap-2 rounded-lg bg-primary px-6 py-3 font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {searchMutation.isPending ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Search className="h-5 w-5" />
            )}
            搜索
          </button>
        </div>

        {/* Advanced Options Toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <SlidersHorizontal className="h-4 w-4" />
          高级选项
        </button>

        {/* Advanced Options */}
        {showAdvanced && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 rounded-lg border p-4">
            <div>
              <label className="block text-sm font-medium mb-1">返回数量</label>
              <input
                type="number"
                value={topK}
                onChange={(e) => setTopK(Math.max(1, Math.min(50, parseInt(e.target.value) || 10)))}
                min={1}
                max={50}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">最低相似度</label>
              <input
                type="number"
                value={minScore}
                onChange={(e) => setMinScore(Math.max(0, Math.min(1, parseFloat(e.target.value) || 0)))}
                min={0}
                max={1}
                step={0.1}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">限定研报</label>
              <select
                value={selectedReportId || ''}
                onChange={(e) => setSelectedReportId(e.target.value ? parseInt(e.target.value) : undefined)}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              >
                <option value="">全部研报</option>
                {reportsData?.items.map((report) => (
                  <option key={report.id} value={report.id}>
                    {report.title}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      <div className="space-y-4">
        {lastQuery && (
          <div className="text-sm text-muted-foreground">
            搜索 "{lastQuery}" 找到 {results.length} 个结果
          </div>
        )}

        {searchMutation.isPending ? (
          <div className="flex h-48 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : results.length === 0 && lastQuery ? (
          <div className="flex h-48 flex-col items-center justify-center rounded-lg border border-dashed">
            <FileText className="h-12 w-12 text-muted-foreground/50" />
            <p className="mt-4 text-muted-foreground">没有找到相关内容</p>
            <p className="text-sm text-muted-foreground">尝试使用不同的关键词或降低最低相似度</p>
          </div>
        ) : results.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center rounded-lg border border-dashed">
            <Search className="h-12 w-12 text-muted-foreground/50" />
            <p className="mt-4 text-muted-foreground">输入关键词开始搜索</p>
          </div>
        ) : (
          <div className="space-y-3">
            {results.map((result, index) => (
              <div
                key={result.chunk_id}
                className="rounded-lg border bg-card p-4 hover:bg-muted/30 transition-colors"
              >
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">#{index + 1}</span>
                    <button
                      onClick={() => result.report_id && navigate(`/research/${result.report_id}`)}
                      className="text-sm font-medium text-primary hover:underline flex items-center gap-1"
                    >
                      {result.report_title}
                      <ExternalLink className="h-3 w-3" />
                    </button>
                  </div>
                  <span
                    className={cn(
                      'rounded-full px-2 py-0.5 text-xs font-medium',
                      getScoreColor(result.score)
                    )}
                  >
                    {(result.score * 100).toFixed(1)}%
                  </span>
                </div>
                {result.section_title && (
                  <div className="text-xs text-muted-foreground mb-2">
                    章节: {result.section_title}
                    {result.page_start && ` | 第 ${result.page_start} 页`}
                  </div>
                )}
                <p className="text-sm whitespace-pre-wrap line-clamp-4">
                  {result.content}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
