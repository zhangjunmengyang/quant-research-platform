/**
 * Stock Hub - 因子评估库
 */

import { useState, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Search, Trash2, Eye, Tag, Loader2, ChevronLeft, ChevronRight } from 'lucide-react'
import { stockApi } from '@/features/stock-hub'
import type { FactorEvaluationItem } from '@/features/stock-hub'

const PAGE_SIZE = 20

export function Component() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [items, setItems] = useState<FactorEvaluationItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [search, setSearch] = useState('')
  const [factorName, setFactorName] = useState('')
  const [selectedTag, setSelectedTag] = useState('')
  const [page, setPage] = useState(1)

  const [tags, setTags] = useState<string[]>([])
  const [deletingUuid, setDeletingUuid] = useState<string | null>(null)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // Fetch tags on mount
  useEffect(() => {
    stockApi.getEvaluationTags().then(setTags).catch(() => {})
  }, [])

  // Fetch evaluations when filters/page change
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    stockApi
      .listEvaluations({
        search: search || undefined,
        factor_name: factorName || undefined,
        tags: selectedTag || undefined,
        page,
        page_size: PAGE_SIZE,
      })
      .then((resp) => {
        if (cancelled) return
        setItems(resp.items)
        setTotal(resp.total)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [search, factorName, selectedTag, page])

  const handleDelete = useCallback(async (uuid: string) => {
    if (!window.confirm(t('stockHub.confirmDelete'))) return
    setDeletingUuid(uuid)
    try {
      await stockApi.deleteEvaluation(uuid)
      setItems((prev) => prev.filter((item) => item.uuid !== uuid))
      setTotal((prev) => prev - 1)
    } catch (err) {
      console.error('Delete evaluation failed:', err)
    } finally {
      setDeletingUuid(null)
    }
  }, [])

  const handleView = useCallback((uuid: string) => {
    navigate('/stock-hub/evaluations/' + uuid)
  }, [navigate])

  const formatDate = useCallback((dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return dateStr
    }
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('stockHub.evaluationLibrary') || '因子评估库'}</h1>

      {/* Filter bar */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder={t('stockHub.searchEvaluations')}
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="w-full rounded-md border bg-background pl-10 pr-4 py-2 text-sm"
          />
        </div>
        <input
          type="text"
          placeholder={t('stockHub.filterByFactor')}
          value={factorName}
          onChange={(e) => { setFactorName(e.target.value); setPage(1) }}
          className="w-48 rounded-md border bg-background px-3 py-2 text-sm"
        />
        <div className="relative">
          <Tag className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <select
            value={selectedTag}
            onChange={(e) => { setSelectedTag(e.target.value); setPage(1) }}
            className="rounded-md border bg-background pl-10 pr-4 py-2 text-sm"
          >
            <option value="">{t('stockHub.allTags')}</option>
            {tags.map((tag) => (
              <option key={tag} value={tag}>{tag}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="flex h-32 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      ) : items.length === 0 ? (
        /* Empty state */
        <div className="flex h-32 items-center justify-center text-muted-foreground">
          {t('stockHub.noEvaluations')}
        </div>
      ) : (
        /* Evaluation cards */
        <div className="grid gap-3">
          {items.map((item) => (
            <div
              key={item.uuid}
              className="rounded-lg border p-4 hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{item.title}</span>
                    <span className="rounded bg-muted px-2 py-0.5 text-xs shrink-0">
                      {item.factor_name}
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center gap-2 flex-wrap">
                    {item.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary"
                      >
                        {tag}
                      </span>
                    ))}
                    <span className="text-xs text-muted-foreground">
                      {formatDate(item.created_at)}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-4">
                  <button
                    onClick={() => handleView(item.uuid)}
                    className="flex items-center gap-1 rounded-md border px-3 py-1.5 text-xs hover:bg-accent"
                  >
                    <Eye className="h-3 w-3" />
                    {t('common.view', '查看')}
                  </button>
                  <button
                    onClick={() => handleDelete(item.uuid)}
                    disabled={deletingUuid === item.uuid}
                    className="flex items-center gap-1 rounded-md border border-destructive/50 px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10 disabled:opacity-50"
                  >
                    {deletingUuid === item.uuid ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Trash2 className="h-3 w-3" />
                    )}
                    {t('common.delete', '删除')}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm disabled:opacity-50"
          >
            <ChevronLeft className="h-4 w-4" />
            {t('common.prevPage', '上一页')}
          </button>
          <span className="text-sm text-muted-foreground">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm disabled:opacity-50"
          >
            {t('common.nextPage', '下一页')}
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  )
}
