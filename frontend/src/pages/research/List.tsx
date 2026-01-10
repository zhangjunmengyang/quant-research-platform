/**
 * Research Reports List Page
 * 研报列表页 - 展示所有研报，支持上传和管理
 */

import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText,
  Upload,
  Loader2,
  Calendar,
  Trash2,
  Play,
  FolderOpen,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  Sparkles,
  ExternalLink,
} from 'lucide-react'
import { useReports, useReportMutations, useProcessingStatus } from '@/features/research'
import type { Report, ReportListParams, ReportStatus } from '@/features/research'
import { STATUS_LABELS, STATUS_COLORS } from '@/features/research'
import { cn } from '@/lib/utils'
import { FilterToolbar } from '@/components/ui/filter-toolbar'
import { FilterSelect, type SelectOption } from '@/components/ui/filter-select'
import { Pagination } from '@/components/ui/pagination'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'

// 状态筛选选项
const STATUS_FILTER_OPTIONS: SelectOption[] = [
  { value: '', label: '全部状态' },
  { value: 'ready', label: STATUS_LABELS.ready },
  { value: 'uploaded', label: STATUS_LABELS.uploaded },
  { value: 'parsing', label: STATUS_LABELS.parsing },
  { value: 'failed', label: STATUS_LABELS.failed },
]

export function Component() {
  const navigate = useNavigate()
  const [params, setParams] = useState<ReportListParams>({ page: 1, page_size: 20 })
  const [searchInput, setSearchInput] = useState('')
  const { data, isLoading, isError, error, refetch } = useReports(params)
  const { upload, process, delete: deleteReport, scanUpload } = useReportMutations()

  // 上传对话框
  const [isUploadOpen, setIsUploadOpen] = useState(false)
  const [uploadFiles, setUploadFiles] = useState<File[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 扫描上传对话框
  const [isScanOpen, setIsScanOpen] = useState(false)
  const [scanDirectory, setScanDirectory] = useState('')
  const [scanRecursive, setScanRecursive] = useState(true)
  const [scanAutoProcess, setScanAutoProcess] = useState(false)

  // 处理中的研报 ID (用于轮询状态)
  const [processingId, setProcessingId] = useState<number | null>(null)
  useProcessingStatus(processingId, !!processingId, 2000)

  const handleSearch = () => {
    setParams({ ...params, search: searchInput, page: 1 })
  }

  const handleStatusFilter = (status: string | undefined) => {
    setParams({ ...params, status: status as ReportStatus | undefined, page: 1 })
  }

  const handleClearFilter = () => {
    setParams({ page: 1, page_size: 20 })
    setSearchInput('')
  }

  const hasActiveFilters = !!(params.search || params.status)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []).filter((f) =>
      f.name.toLowerCase().endsWith('.pdf')
    )
    setUploadFiles(files)
    if (files.length > 0) {
      setIsUploadOpen(true)
    }
  }

  const handleUpload = async () => {
    for (const file of uploadFiles) {
      try {
        await upload.mutateAsync({ file })
      } catch (err) {
        console.error('Upload failed:', err)
      }
    }
    setIsUploadOpen(false)
    setUploadFiles([])
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
    // 确保上传完成后刷新列表
    refetch()
  }

  const handleProcess = async (report: Report) => {
    try {
      await process.mutateAsync({ id: report.id })
      setProcessingId(report.id)
    } catch (err) {
      console.error('Process failed:', err)
    }
  }

  const handleDelete = async (e: React.MouseEvent, report: Report) => {
    e.stopPropagation()
    if (confirm(`确定要删除研报「${report.title}」吗?`)) {
      await deleteReport.mutateAsync(report.id)
    }
  }

  const handleScanUpload = async () => {
    if (!scanDirectory.trim()) {
      alert('请输入目录路径')
      return
    }
    try {
      const result = await scanUpload.mutateAsync({
        directory: scanDirectory.trim(),
        recursive: scanRecursive,
        auto_process: scanAutoProcess,
      })
      alert(`成功上传 ${result.uploaded} 个研报`)
      setIsScanOpen(false)
      setScanDirectory('')
      // 确保扫描上传完成后刷新列表
      refetch()
    } catch (err) {
      console.error('Scan upload failed:', err)
      alert('扫描上传失败')
    }
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getStatusIcon = (status: ReportStatus) => {
    switch (status) {
      case 'ready':
        return <CheckCircle className="h-4 w-4" />
      case 'failed':
        return <AlertCircle className="h-4 w-4" />
      case 'uploaded':
        return <Clock className="h-4 w-4" />
      default:
        return <Loader2 className="h-4 w-4 animate-spin" />
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

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
          <h1 className="text-2xl font-bold">研报库</h1>
          <p className="text-muted-foreground">共 {data?.total ?? 0} 份研报</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('/research/search')}
            className="flex items-center gap-2 rounded-md border px-4 py-2 text-sm hover:bg-muted"
          >
            <Sparkles className="h-4 w-4" />
            语义搜索
          </button>
          <button
            onClick={() => setIsScanOpen(true)}
            className="flex items-center gap-2 rounded-md border px-4 py-2 text-sm hover:bg-muted"
          >
            <FolderOpen className="h-4 w-4" />
            扫描目录
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <Upload className="h-4 w-4" />
            上传研报
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <FilterToolbar
        searchValue={searchInput}
        onSearchChange={setSearchInput}
        onSearch={handleSearch}
        searchPlaceholder="搜索研报..."
        showRefresh
        onRefresh={() => refetch()}
        hasActiveFilters={hasActiveFilters}
        onReset={handleClearFilter}
      >
        <FilterSelect
          label="状态"
          options={STATUS_FILTER_OPTIONS}
          value={params.status}
          onChange={handleStatusFilter}
        />
      </FilterToolbar>

      {/* Reports List */}
      <div className="space-y-4">
        {data?.items.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center rounded-lg border border-dashed">
            <FileText className="h-12 w-12 text-muted-foreground/50" />
            <p className="mt-4 text-muted-foreground">
              {params.search || params.status ? '没有匹配的研报' : '还没有研报'}
            </p>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="mt-4 flex items-center gap-2 text-sm text-primary hover:underline"
            >
              <Upload className="h-4 w-4" />
              上传第一份研报
            </button>
          </div>
        ) : (
          data?.items.map((report) => (
            <div
              key={report.id}
              onClick={() => navigate(`/research/${report.id}`)}
              className="group cursor-pointer rounded-lg border bg-card p-4 transition-colors hover:bg-muted/30"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <h3 className="font-medium truncate flex items-center gap-1">
                      {report.title}
                      <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-50" />
                    </h3>
                    <span
                      className={cn(
                        'flex items-center gap-1 rounded-full px-2 py-0.5 text-xs',
                        STATUS_COLORS[report.status as ReportStatus]
                      )}
                    >
                      {getStatusIcon(report.status as ReportStatus)}
                      {STATUS_LABELS[report.status as ReportStatus]}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground truncate">{report.filename}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                    <span>{formatFileSize(report.file_size)}</span>
                    {report.page_count > 0 && <span>{report.page_count} 页</span>}
                    {report.author && <span>{report.author}</span>}
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      <span>{formatDate(report.created_at)}</span>
                    </div>
                    {report.progress > 0 && report.progress < 100 && (
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-20 rounded-full bg-secondary">
                          <div
                            className="h-full rounded-full bg-primary transition-all"
                            style={{ width: `${report.progress}%` }}
                          />
                        </div>
                        <span>{report.progress}%</span>
                      </div>
                    )}
                  </div>
                  {report.error_message && (
                    <p className="mt-2 text-xs text-destructive">{report.error_message}</p>
                  )}
                </div>
                <div className="ml-4 flex items-center gap-2">
                  {(report.status === 'uploaded' || report.status === 'failed') && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleProcess(report)
                      }}
                      disabled={process.isPending}
                      className="rounded p-2 hover:bg-primary/10 hover:text-primary"
                      title={report.status === 'failed' ? '重新处理' : '开始处理'}
                    >
                      {report.status === 'failed' ? (
                        <RefreshCw className="h-4 w-4" />
                      ) : (
                        <Play className="h-4 w-4" />
                      )}
                    </button>
                  )}
                  <button
                    onClick={(e) => handleDelete(e, report)}
                    className="rounded p-2 opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                    title="删除"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {data && data.total > data.page_size && (
        <Pagination
          page={params.page ?? 1}
          pageSize={data.page_size}
          total={data.total}
          onPageChange={(page) => setParams({ ...params, page })}
          position="center"
        />
      )}

      {/* Upload Dialog */}
      <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>上传研报</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground mb-4">
              即将上传 {uploadFiles.length} 个文件:
            </p>
            <ul className="space-y-2 max-h-60 overflow-auto">
              {uploadFiles.map((file, i) => (
                <li key={i} className="flex items-center gap-2 text-sm overflow-hidden">
                  <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="truncate" title={file.name}>{file.name}</span>
                  <span className="shrink-0 text-muted-foreground whitespace-nowrap">({formatFileSize(file.size)})</span>
                </li>
              ))}
            </ul>
          </div>
          <DialogFooter>
            <button
              onClick={() => {
                setIsUploadOpen(false)
                setUploadFiles([])
              }}
              className="rounded-md border px-4 py-2 text-sm hover:bg-muted"
            >
              取消
            </button>
            <button
              onClick={handleUpload}
              disabled={upload.isPending}
              className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {upload.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              开始上传
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Scan Upload Dialog */}
      <Dialog open={isScanOpen} onOpenChange={setIsScanOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>扫描目录上传</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="mb-1 block text-sm font-medium">目录路径</label>
              <input
                type="text"
                value={scanDirectory}
                onChange={(e) => setScanDirectory(e.target.value)}
                placeholder="/path/to/reports"
                className="w-full rounded-md border bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={scanRecursive}
                  onChange={(e) => setScanRecursive(e.target.checked)}
                  className="rounded"
                />
                递归扫描子目录
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={scanAutoProcess}
                  onChange={(e) => setScanAutoProcess(e.target.checked)}
                  className="rounded"
                />
                自动开始处理
              </label>
            </div>
          </div>
          <DialogFooter>
            <button
              onClick={() => setIsScanOpen(false)}
              className="rounded-md border px-4 py-2 text-sm hover:bg-muted"
            >
              取消
            </button>
            <button
              onClick={handleScanUpload}
              disabled={scanUpload.isPending}
              className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {scanUpload.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FolderOpen className="h-4 w-4" />
              )}
              开始扫描
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
