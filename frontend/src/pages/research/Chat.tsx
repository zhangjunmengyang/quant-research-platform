/**
 * Research Chat Page
 * 研报对话页 - 左 PDF 右 Chat 布局
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Send,
  Loader2,
  FileText,
  MessageSquare,
  Bot,
  User,
  Trash2,
  Plus,
  PanelLeftClose,
  PanelLeft,
} from 'lucide-react'
import {
  useReport,
  useConversations,
  useMessages,
  useConversationMutations,
  useModels,
  researchApi,
  PDFViewer,
  ModelSelector,
} from '@/features/research'
import type { Message, Conversation } from '@/features/research'
import { cn } from '@/lib/utils'

export function Component() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const reportId = id ? parseInt(id, 10) : null

  const { data: report, isLoading: reportLoading } = useReport(reportId)
  const { data: conversations = [], refetch: refetchConversations } = useConversations()
  const { data: modelsData } = useModels()
  const { create: createConv, delete: deleteConv } = useConversationMutations()

  // 当前对话
  const [currentConvId, setCurrentConvId] = useState<number | null>(null)
  const { data: messages = [], refetch: refetchMessages } = useMessages(currentConvId)

  // 输入和流式响应
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [localMessages, setLocalMessages] = useState<Message[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('')

  // UI 状态
  const [showConvList, setShowConvList] = useState(true)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // 设置默认模型
  useEffect(() => {
    if (modelsData?.default_model && !selectedModel) {
      setSelectedModel(modelsData.default_model)
    }
  }, [modelsData, selectedModel])

  // 筛选当前研报的对话
  const reportConversations = conversations.filter((c) => c.report_id === reportId)

  // 同步远程消息到本地
  useEffect(() => {
    if (messages.length > 0) {
      setLocalMessages(messages)
    }
  }, [messages])

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [localMessages, streamingContent])

  // 创建新对话
  const handleCreateConversation = async () => {
    try {
      const conv = await createConv.mutateAsync({
        title: `与「${report?.title}」的对话`,
        report_id: reportId ?? undefined,
      })
      setCurrentConvId(conv.id)
      setLocalMessages([])
      refetchConversations()
    } catch (err) {
      console.error('Create conversation failed:', err)
    }
  }

  // 切换对话
  const handleSelectConversation = (conv: Conversation) => {
    setCurrentConvId(conv.id)
    setLocalMessages([])
    setStreamingContent('')
  }

  // 删除对话
  const handleDeleteConversation = async (e: React.MouseEvent, convId: number) => {
    e.stopPropagation()
    if (confirm('确定要删除这个对话吗?')) {
      await deleteConv.mutateAsync(convId)
      if (currentConvId === convId) {
        setCurrentConvId(null)
        setLocalMessages([])
      }
      refetchConversations()
    }
  }

  // 发送消息 (流式)
  const handleSendMessage = useCallback(async () => {
    if (!input.trim() || !currentConvId || isStreaming) return

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
    }

    // 添加用户消息到本地
    setLocalMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsStreaming(true)
    setStreamingContent('')

    // 创建占位的 assistant 消息
    const assistantMessage: Message = {
      role: 'assistant',
      content: '',
    }
    setLocalMessages((prev) => [...prev, assistantMessage])

    let fullContent = ''

    try {
      researchApi.chatStream(
        currentConvId,
        {
          message: userMessage.content,
          report_id: reportId ?? undefined,
          model_key: selectedModel || undefined,
        },
        (chunk) => {
          if (chunk.type === 'content' && chunk.content) {
            fullContent += chunk.content
            setStreamingContent(fullContent)
          }
        },
        (error) => {
          console.error('Stream error:', error)
          setIsStreaming(false)
        },
        () => {
          // 完成后更新本地消息
          setLocalMessages((prev) => {
            const updated = [...prev]
            const lastIndex = updated.length - 1
            if (lastIndex >= 0 && updated[lastIndex].role === 'assistant') {
              updated[lastIndex] = {
                ...updated[lastIndex],
                content: fullContent,
              }
            }
            return updated
          })
          setIsStreaming(false)
          setStreamingContent('')
          refetchMessages()
        }
      )
    } catch (err) {
      console.error('Send message failed:', err)
      setIsStreaming(false)
    }
  }, [input, currentConvId, isStreaming, reportId, selectedModel, refetchMessages])

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // 格式化时间
  const formatTime = (dateStr?: string) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  if (reportLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!report) {
    return (
      <div className="flex h-screen flex-col items-center justify-center">
        <p className="text-muted-foreground">研报不存在</p>
        <button
          onClick={() => navigate('/research')}
          className="mt-4 flex items-center gap-2 text-primary hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          返回研报列表
        </button>
      </div>
    )
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/research')}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            返回
          </button>
          <div className="h-4 w-px bg-border" />
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium truncate max-w-md">{report.title}</span>
          </div>
        </div>
      </div>

      {/* Main Content: Left PDF + Right Chat */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: PDF Viewer */}
        <div className="w-1/2 border-r">
          <PDFViewer reportId={report.id} className="h-full" />
        </div>

        {/* Right: Chat Area */}
        <div className="w-1/2 flex">
          {/* Conversation List Sidebar */}
          {showConvList && (
            <div className="w-56 border-r flex flex-col bg-muted/30">
              <div className="p-3 border-b flex items-center justify-between">
                <span className="text-sm font-medium">对话列表</span>
                <button
                  onClick={() => setShowConvList(false)}
                  className="p-1 rounded hover:bg-muted"
                  title="收起"
                >
                  <PanelLeftClose className="h-4 w-4" />
                </button>
              </div>
              <div className="p-2">
                <button
                  onClick={handleCreateConversation}
                  disabled={createConv.isPending}
                  className="w-full flex items-center justify-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                >
                  {createConv.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4" />
                  )}
                  新建对话
                </button>
              </div>
              <div className="flex-1 overflow-auto p-2">
                {reportConversations.length === 0 ? (
                  <p className="text-center text-sm text-muted-foreground py-4">
                    还没有对话
                  </p>
                ) : (
                  <div className="space-y-1">
                    {reportConversations.map((conv) => (
                      <div
                        key={conv.id}
                        onClick={() => handleSelectConversation(conv)}
                        className={cn(
                          'group flex items-center justify-between rounded-md px-3 py-2 text-sm cursor-pointer',
                          currentConvId === conv.id
                            ? 'bg-primary/10 text-primary'
                            : 'hover:bg-muted'
                        )}
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <MessageSquare className="h-4 w-4 shrink-0" />
                          <span className="truncate">{conv.title}</span>
                        </div>
                        <button
                          onClick={(e) => handleDeleteConversation(e, conv.id)}
                          className="shrink-0 rounded p-1 opacity-0 hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Chat Content */}
          <div className="flex-1 flex flex-col">
            {/* Toggle button when sidebar is hidden */}
            {!showConvList && (
              <div className="absolute left-1/2 top-16 z-10">
                <button
                  onClick={() => setShowConvList(true)}
                  className="p-1 rounded bg-background border shadow-sm hover:bg-muted"
                  title="展开对话列表"
                >
                  <PanelLeft className="h-4 w-4" />
                </button>
              </div>
            )}

            {!currentConvId ? (
              <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
                <Bot className="h-16 w-16 mb-4 opacity-50" />
                <p>选择或创建一个对话开始</p>
              </div>
            ) : (
              <>
                {/* Messages */}
                <div className="flex-1 overflow-auto p-4 space-y-4">
                  {localMessages.length === 0 && !isStreaming ? (
                    <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                      <MessageSquare className="h-12 w-12 mb-4 opacity-50" />
                      <p>开始提问吧</p>
                      <p className="text-sm mt-2">我会基于研报内容为你解答</p>
                    </div>
                  ) : (
                    localMessages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={cn(
                          'flex gap-3',
                          msg.role === 'user' ? 'justify-end' : 'justify-start'
                        )}
                      >
                        {msg.role === 'assistant' && (
                          <div className="shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                            <Bot className="h-4 w-4 text-primary" />
                          </div>
                        )}
                        <div
                          className={cn(
                            'max-w-[80%] rounded-lg px-4 py-2',
                            msg.role === 'user'
                              ? 'bg-primary text-primary-foreground'
                              : 'bg-muted'
                          )}
                        >
                          <p className="text-sm whitespace-pre-wrap">
                            {msg.role === 'assistant' && idx === localMessages.length - 1 && isStreaming
                              ? streamingContent || '...'
                              : msg.content}
                          </p>
                          {msg.created_at && (
                            <p className="text-xs opacity-70 mt-1">{formatTime(msg.created_at)}</p>
                          )}
                        </div>
                        {msg.role === 'user' && (
                          <div className="shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                            <User className="h-4 w-4" />
                          </div>
                        )}
                      </div>
                    ))
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="border-t p-4">
                  <div className="flex gap-2 items-end">
                    <ModelSelector
                      value={selectedModel}
                      onChange={setSelectedModel}
                      disabled={isStreaming}
                    />
                    <textarea
                      ref={inputRef}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="输入问题... (Shift+Enter 换行)"
                      rows={1}
                      className="flex-1 resize-none rounded-md border bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                      disabled={isStreaming}
                    />
                    <button
                      onClick={handleSendMessage}
                      disabled={!input.trim() || isStreaming}
                      className="shrink-0 rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                    >
                      {isStreaming ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Send className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
