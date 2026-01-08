/**
 * Research Report Detail Page
 * 研报详情页 - 展示研报内容、切块、和相关功能
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  FileText,
  Loader2,
  Calendar,
  User,
  ExternalLink,
  Layers,
  Hash,
  ChevronDown,
  ChevronRight,
  Search,
  Sparkles,
} from 'lucide-react'
import {
  useReport,
  useReportChunks,
  useSimilarChunks,
  STATUS_LABELS,
  STATUS_COLORS,
} from '@/features/research'
import type { Chunk, ReportStatus, SimilarChunkItem } from '@/features/research'
import { cn } from '@/lib/utils'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

// 切块类型颜色
const CHUNK_TYPE_COLORS: Record<string, string> = {
  title: 'bg-purple-100 text-purple-800',
  heading: 'bg-blue-100 text-blue-800',
  paragraph: 'bg-gray-100 text-gray-800',
  list: 'bg-green-100 text-green-800',
  table: 'bg-yellow-100 text-yellow-800',
  code: 'bg-orange-100 text-orange-800',
  text: 'bg-gray-100 text-gray-800',
}

export function Component() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const reportId = id ? parseInt(id, 10) : null

  const { data: report, isLoading: reportLoading, isError } = useReport(reportId)
  const [chunkParams, setChunkParams] = useState({ page: 1, page_size: 20 })
  const { data: chunksData, isLoading: chunksLoading } = useReportChunks(reportId, chunkParams)

  const similarChunksMutation = useSimilarChunks()

  // 展开的切块
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set())
  // 相似切块对话框
  const [similarDialogOpen, setSimilarDialogOpen] = useState(false)
  const [selectedChunk, setSelectedChunk] = useState<Chunk | null>(null)
  const [similarChunks, setSimilarChunks] = useState<SimilarChunkItem[]>([])

  const toggleChunk = (chunkId: string) => {
    const newSet = new Set(expandedChunks)
    if (newSet.has(chunkId)) {
      newSet.delete(chunkId)
    } else {
      newSet.add(chunkId)
    }
    setExpandedChunks(newSet)
  }

  const handleFindSimilar = async (chunk: Chunk) => {
    setSelectedChunk(chunk)
    setSimilarDialogOpen(true)
    try {
      const result = await similarChunksMutation.mutateAsync({
        chunk_id: chunk.chunk_id,
        top_k: 5,
        exclude_same_report: true,
      })
      setSimilarChunks(result.similar_chunks)
    } catch (err) {
      console.error('Failed to find similar chunks:', err)
    }
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  if (reportLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (isError || !report) {
    return (
      <div className="flex h-64 flex-col items-center justify-center text-destructive">
        <p>研报不存在或加载失败</p>
        <button
          onClick={() => navigate('/research')}
          className="mt-4 text-sm text-primary hover:underline"
        >
          返回列表
        </button>
      </div>
    )
  }

  const canShowChunks = ['chunked', 'embedded', 'indexing', 'ready'].includes(report.status)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/research')}
          className="rounded p-2 hover:bg-muted"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{report.title}</h1>
          <p className="text-sm text-muted-foreground">{report.filename}</p>
        </div>
        <span
          className={cn(
            'rounded-full px-3 py-1 text-sm',
            STATUS_COLORS[report.status as ReportStatus]
          )}
        >
          {STATUS_LABELS[report.status as ReportStatus]}
        </span>
      </div>

      {/* Report Info */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-lg border p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <FileText className="h-4 w-4" />
            文件大小
          </div>
          <div className="font-medium">{formatFileSize(report.file_size)}</div>
        </div>
        <div className="rounded-lg border p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Layers className="h-4 w-4" />
            页数
          </div>
          <div className="font-medium">{report.page_count || '-'} 页</div>
        </div>
        {report.author && (
          <div className="rounded-lg border p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <User className="h-4 w-4" />
              作者
            </div>
            <div className="font-medium">{report.author}</div>
          </div>
        )}
        <div className="rounded-lg border p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Calendar className="h-4 w-4" />
            上传时间
          </div>
          <div className="font-medium text-sm">{formatDate(report.created_at)}</div>
        </div>
      </div>

      {/* Source URL */}
      {report.source_url && (
        <div className="rounded-lg border p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <ExternalLink className="h-4 w-4" />
            来源链接
          </div>
          <a
            href={report.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline break-all"
          >
            {report.source_url}
          </a>
        </div>
      )}

      {/* Processing Progress */}
      {report.progress > 0 && report.progress < 100 && (
        <div className="rounded-lg border p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-muted-foreground">处理进度</span>
            <span className="text-sm font-medium">{report.progress}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-secondary">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${report.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error Message */}
      {report.error_message && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{report.error_message}</p>
        </div>
      )}

      {/* Chunks Section */}
      {canShowChunks && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Hash className="h-5 w-5" />
              文档切块
              {chunksData && (
                <span className="text-sm font-normal text-muted-foreground">
                  (共 {chunksData.total} 个)
                </span>
              )}
            </h2>
          </div>

          {chunksLoading ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : chunksData?.chunks.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              暂无切块数据
            </div>
          ) : (
            <div className="space-y-2">
              {chunksData?.chunks.map((chunk) => {
                const isExpanded = expandedChunks.has(chunk.chunk_id)
                return (
                  <div
                    key={chunk.chunk_id}
                    className="rounded-lg border overflow-hidden"
                  >
                    {/* Chunk Header */}
                    <div
                      className="flex items-center gap-3 p-3 cursor-pointer hover:bg-muted/50"
                      onClick={() => toggleChunk(chunk.chunk_id)}
                    >
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 shrink-0" />
                      ) : (
                        <ChevronRight className="h-4 w-4 shrink-0" />
                      )}
                      <span
                        className={cn(
                          'rounded px-2 py-0.5 text-xs shrink-0',
                          CHUNK_TYPE_COLORS[chunk.chunk_type] || CHUNK_TYPE_COLORS.text
                        )}
                      >
                        {chunk.chunk_type}
                      </span>
                      <span className="text-sm font-medium truncate flex-1">
                        {chunk.section_title || `切块 #${chunk.chunk_index + 1}`}
                      </span>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
                        {chunk.page_start && (
                          <span>第 {chunk.page_start} 页</span>
                        )}
                        <span>{chunk.token_count} tokens</span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleFindSimilar(chunk)
                        }}
                        className="rounded p-1 hover:bg-primary/10 hover:text-primary"
                        title="查找相似切块"
                      >
                        <Search className="h-4 w-4" />
                      </button>
                    </div>
                    {/* Chunk Content */}
                    {isExpanded && (
                      <div className="border-t p-4 bg-muted/30">
                        <pre className="whitespace-pre-wrap text-sm font-mono">
                          {chunk.content}
                        </pre>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Chunks Pagination */}
          {chunksData && chunksData.total > chunksData.page_size && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setChunkParams({ ...chunkParams, page: chunkParams.page - 1 })}
                disabled={chunkParams.page <= 1}
                className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
              >
                上一页
              </button>
              <span className="text-sm text-muted-foreground">
                第 {chunksData.page} / {Math.ceil(chunksData.total / chunksData.page_size)} 页
              </span>
              <button
                onClick={() => setChunkParams({ ...chunkParams, page: chunkParams.page + 1 })}
                disabled={chunkParams.page >= Math.ceil(chunksData.total / chunksData.page_size)}
                className="rounded-md border px-3 py-1 text-sm disabled:opacity-50"
              >
                下一页
              </button>
            </div>
          )}
        </div>
      )}

      {/* Not Ready Message */}
      {!canShowChunks && report.status !== 'failed' && (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <Layers className="h-12 w-12 mx-auto text-muted-foreground/50" />
          <p className="mt-4 text-muted-foreground">
            研报尚未处理完成，无法查看切块
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            当前状态: {STATUS_LABELS[report.status as ReportStatus]}
          </p>
        </div>
      )}

      {/* Similar Chunks Dialog */}
      <Dialog open={similarDialogOpen} onOpenChange={setSimilarDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              相似切块
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Reference Chunk */}
            {selectedChunk && (
              <div className="rounded-lg border p-3 bg-muted/50">
                <div className="text-xs text-muted-foreground mb-2">参考切块</div>
                <p className="text-sm line-clamp-3">{selectedChunk.content}</p>
              </div>
            )}

            {/* Similar Chunks List */}
            {similarChunksMutation.isPending ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : similarChunks.length === 0 ? (
              <div className="flex h-32 items-center justify-center text-muted-foreground">
                未找到相似切块
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-sm font-medium">
                  找到 {similarChunks.length} 个相似切块
                </div>
                {similarChunks.map((chunk, index) => (
                  <div key={chunk.chunk_id} className="rounded-lg border p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-primary">
                        {chunk.report_title}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        相似度: {(chunk.score * 100).toFixed(1)}%
                      </span>
                    </div>
                    {chunk.section_title && (
                      <div className="text-xs text-muted-foreground mb-1">
                        章节: {chunk.section_title}
                      </div>
                    )}
                    <p className="text-sm line-clamp-4">{chunk.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
