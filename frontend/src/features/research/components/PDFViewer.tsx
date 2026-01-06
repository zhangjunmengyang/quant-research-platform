/**
 * PDF Viewer Component
 * 研报 PDF 预览组件 - 滚动模式
 */

import { useState, useCallback } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { Loader2, ZoomIn, ZoomOut } from 'lucide-react'
import { researchApi } from '../api'
import { cn } from '@/lib/utils'

import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

// 配置 PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

interface PDFViewerProps {
  reportId: number
  className?: string
}

export function PDFViewer({ reportId, className }: PDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0)
  const [scale, setScale] = useState<number>(1.0)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const pdfUrl = researchApi.getPdfUrl(reportId)

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages)
    setLoading(false)
    setError(null)
  }, [])

  const onDocumentLoadError = useCallback((err: Error) => {
    console.error('PDF load error:', err)
    setError('PDF 加载失败')
    setLoading(false)
  }, [])

  const zoomIn = useCallback(() => {
    setScale((prev) => Math.min(2.0, prev + 0.2))
  }, [])

  const zoomOut = useCallback(() => {
    setScale((prev) => Math.max(0.5, prev - 0.2))
  }, [])

  const resetZoom = useCallback(() => {
    setScale(1.0)
  }, [])

  if (error) {
    return (
      <div className={cn('flex flex-col items-center justify-center h-full bg-muted/30', className)}>
        <p className="text-destructive">{error}</p>
        <button
          onClick={() => {
            setLoading(true)
            setError(null)
          }}
          className="mt-4 text-sm text-primary hover:underline"
        >
          重试
        </button>
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* 工具栏 */}
      <div className="flex items-center justify-between border-b px-4 py-2 bg-background shrink-0">
        <span className="text-sm text-muted-foreground">
          {numPages > 0 ? `共 ${numPages} 页` : '加载中...'}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={zoomOut}
            disabled={scale <= 0.5}
            className="p-1 rounded hover:bg-muted disabled:opacity-50"
            title="缩小"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <button
            onClick={resetZoom}
            className="text-sm w-12 text-center hover:bg-muted rounded px-1"
            title="重置缩放"
          >
            {Math.round(scale * 100)}%
          </button>
          <button
            onClick={zoomIn}
            disabled={scale >= 2.0}
            className="p-1 rounded hover:bg-muted disabled:opacity-50"
            title="放大"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* PDF 内容区域 - 滚动显示所有页面 */}
      <div className="flex-1 overflow-auto bg-muted/30">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}
        <Document
          file={pdfUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={onDocumentLoadError}
          loading={null}
          className="flex flex-col items-center py-4 gap-4"
        >
          {numPages > 0 &&
            Array.from({ length: numPages }, (_, index) => (
              <Page
                key={`page_${index + 1}`}
                pageNumber={index + 1}
                scale={scale}
                loading={
                  <div className="flex items-center justify-center h-[800px] w-[600px] bg-white shadow-lg">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                }
                className="shadow-lg"
              />
            ))}
        </Document>
      </div>
    </div>
  )
}
