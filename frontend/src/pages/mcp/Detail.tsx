/**
 * MCP Server Detail Page
 * MCP 服务器详情页
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Server,
  Play,
  Square,
  RefreshCw,
  Loader2,
  Wrench,
  ArrowLeft,
  Copy,
  Check,
  ExternalLink,
  Info,
  Settings,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useMCPServer,
  useMCPServerAction,
  useMCPServerTools,
} from '@/features/mcp'
import type { MCPServerStatus, MCPToolInfo } from '@/features/mcp'

// 状态灯颜色配置
const STATUS_LIGHT: Record<MCPServerStatus, { color: string; glow: string; label: string }> = {
  running: {
    color: 'bg-green-500',
    glow: 'shadow-[0_0_8px_2px_rgba(34,197,94,0.6)]',
    label: '运行中',
  },
  stopped: {
    color: 'bg-red-500',
    glow: 'shadow-[0_0_8px_2px_rgba(239,68,68,0.6)]',
    label: '已停止',
  },
  error: {
    color: 'bg-orange-500',
    glow: 'shadow-[0_0_8px_2px_rgba(249,115,22,0.6)]',
    label: '错误',
  },
  starting: {
    color: 'bg-yellow-500',
    glow: 'shadow-[0_0_8px_2px_rgba(234,179,8,0.6)]',
    label: '启动中',
  },
  stopping: {
    color: 'bg-yellow-500',
    glow: 'shadow-[0_0_8px_2px_rgba(234,179,8,0.6)]',
    label: '停止中',
  },
  unresponsive: {
    color: 'bg-gray-500',
    glow: 'shadow-[0_0_8px_2px_rgba(107,114,128,0.6)]',
    label: '无响应',
  },
}

// Tab 类型
type TabType = 'info' | 'tools' | 'config'

// 格式化运行时间
function formatUptime(seconds?: number): string {
  if (!seconds) return '-'
  if (seconds < 60) return `${Math.floor(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${minutes}m`
}

// 状态指示灯组件
function StatusLight({ status, showLabel = false }: { status: MCPServerStatus; showLabel?: boolean }) {
  const config = STATUS_LIGHT[status] || STATUS_LIGHT.stopped
  const isAnimating = status === 'running' || status === 'starting' || status === 'stopping'
  const animationClass = status === 'running' ? 'animate-[pulse_3s_ease-in-out_infinite]' : 'animate-pulse'

  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          'w-2.5 h-2.5 rounded-full',
          config.color,
          config.glow,
          isAnimating && animationClass
        )}
      />
      {showLabel && <span className="text-sm text-muted-foreground">{config.label}</span>}
    </div>
  )
}

// 复制按钮组件
function CopyButton({ text, className }: { text: string; className?: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={handleCopy}
      className={cn(
        'inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md border bg-background hover:bg-accent transition-colors',
        className
      )}
    >
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5 text-green-500" />
          <span>已复制</span>
        </>
      ) : (
        <>
          <Copy className="h-3.5 w-3.5" />
          <span>复制</span>
        </>
      )}
    </button>
  )
}

// 配置模板生成
function generateConfigTemplates(serverName: string, _displayName: string, host: string, port: number) {
  const mcpUrl = `http://${host === 'localhost' ? '127.0.0.1' : host}:${port}/mcp`
  const sseUrl = `http://${host === 'localhost' ? '127.0.0.1' : host}:${port}/sse`

  return {
    claudeCode: {
      name: 'Claude Code',
      description: '在 ~/.claude/settings.json 或项目 .mcp.json 中配置',
      code: JSON.stringify({
        mcpServers: {
          [serverName]: {
            url: mcpUrl,
          },
        },
      }, null, 2),
    },
    cursor: {
      name: 'Cursor',
      description: '在 Cursor Settings > MCP 中添加',
      code: JSON.stringify({
        mcpServers: {
          [serverName]: {
            url: mcpUrl,
            transport: 'http',
          },
        },
      }, null, 2),
    },
    windsurf: {
      name: 'Windsurf',
      description: '在 ~/.codeium/windsurf/mcp_config.json 中配置',
      code: JSON.stringify({
        mcpServers: {
          [serverName]: {
            serverUrl: mcpUrl,
          },
        },
      }, null, 2),
    },
    vscode: {
      name: 'VS Code (Copilot)',
      description: '在 .vscode/mcp.json 或用户设置中配置',
      code: JSON.stringify({
        servers: {
          [serverName]: {
            type: 'http',
            url: mcpUrl,
          },
        },
      }, null, 2),
    },
    generic: {
      name: 'HTTP URL',
      description: '直接使用 HTTP 端点',
      code: mcpUrl,
    },
    sse: {
      name: 'SSE URL',
      description: 'Server-Sent Events 端点',
      code: sseUrl,
    },
  }
}

// 简介 Tab
function InfoTab({ server }: { server: NonNullable<ReturnType<typeof useMCPServer>['data']> }) {
  return (
    <div className="space-y-6">
      {/* 基本信息 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-lg border bg-card p-4">
          <div className="text-sm text-muted-foreground">状态</div>
          <div className="mt-1">
            <StatusLight status={server.status} showLabel />
          </div>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <div className="text-sm text-muted-foreground">端口</div>
          <div className="mt-1 text-lg font-semibold">{server.port}</div>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <div className="text-sm text-muted-foreground">工具数</div>
          <div className="mt-1 text-lg font-semibold">{server.tools_count}</div>
        </div>
        <div className="rounded-lg border bg-card p-4">
          <div className="text-sm text-muted-foreground">运行时长</div>
          <div className="mt-1 text-lg font-semibold">{formatUptime(server.uptime_seconds)}</div>
        </div>
      </div>

      {/* 描述 */}
      <div className="rounded-lg border bg-card p-4">
        <h4 className="font-medium mb-2">服务描述</h4>
        <p className="text-muted-foreground">{server.description}</p>
      </div>

      {/* 连接信息 */}
      <div className="rounded-lg border bg-card p-4">
        <h4 className="font-medium mb-3 flex items-center gap-2">
          <ExternalLink className="h-4 w-4" />
          连接信息
        </h4>
        <div className="space-y-3">
          <div>
            <div className="text-sm text-muted-foreground mb-1">MCP 端点</div>
            <div className="flex items-center gap-2">
              <code className="flex-1 px-3 py-2 bg-muted rounded-md text-sm">
                http://{server.host}:{server.port}/mcp
              </code>
              <CopyButton text={`http://${server.host}:${server.port}/mcp`} />
            </div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground mb-1">健康检查</div>
            <div className="flex items-center gap-2">
              <code className="flex-1 px-3 py-2 bg-muted rounded-md text-sm">
                http://{server.host}:{server.port}/health
              </code>
              <CopyButton text={`http://${server.host}:${server.port}/health`} />
            </div>
          </div>
        </div>
      </div>

      {/* 版本信息 */}
      {server.version && (
        <div className="rounded-lg border bg-card p-4">
          <h4 className="font-medium mb-2">版本信息</h4>
          <p className="text-muted-foreground font-mono">{server.version}</p>
        </div>
      )}
    </div>
  )
}

// 工具列表 Tab
function ToolsTab({ serverName }: { serverName: string }) {
  const { data: tools, isLoading } = useMCPServerTools(serverName)
  const [searchQuery, setSearchQuery] = useState('')

  const filteredTools = tools?.filter(
    (tool) =>
      tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 搜索框 */}
      <div className="relative">
        <input
          type="text"
          placeholder="搜索工具..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full px-4 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      {/* 工具列表 */}
      <div className="rounded-lg border bg-card divide-y">
        {filteredTools && filteredTools.length > 0 ? (
          filteredTools.map((tool: MCPToolInfo) => (
            <div key={tool.name} className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="font-mono text-sm font-medium">{tool.name}</div>
                  <div className="mt-1 text-sm text-muted-foreground">{tool.description}</div>
                </div>
                {tool.category && (
                  <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-muted text-muted-foreground">
                    {tool.category}
                  </span>
                )}
              </div>
              {tool.input_schema && (
                <details className="mt-3">
                  <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                    查看参数
                  </summary>
                  <pre className="mt-2 p-3 bg-muted rounded-md text-xs overflow-x-auto">
                    {JSON.stringify(tool.input_schema, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          ))
        ) : (
          <div className="p-8 text-center text-muted-foreground">
            {searchQuery ? '未找到匹配的工具' : '暂无可用工具'}
          </div>
        )}
      </div>
    </div>
  )
}

// 配置模板 Tab
function ConfigTab({ server }: { server: NonNullable<ReturnType<typeof useMCPServer>['data']> }) {
  const templates = generateConfigTemplates(server.name, server.display_name, server.host, server.port)

  return (
    <div className="space-y-4">
      {/* 所有配置模板 */}
      <div className="grid gap-4">
        {Object.entries(templates).map(([key, template]) => (
          <div key={key} className="rounded-lg border bg-card overflow-hidden">
            <div className="px-4 py-3 border-b bg-muted/30 flex items-center justify-between">
              <div>
                <div className="font-medium text-sm">{template.name}</div>
                <div className="text-xs text-muted-foreground">{template.description}</div>
              </div>
              <CopyButton text={template.code} />
            </div>
            <pre className="p-4 text-sm overflow-x-auto bg-muted/10">
              <code>{template.code}</code>
            </pre>
          </div>
        ))}
      </div>
    </div>
  )
}

// 主页面组件
export function Component() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabType>('info')
  const [actionPending, setActionPending] = useState(false)

  const { data: server, isLoading, refetch } = useMCPServer(name || '')
  const serverAction = useMCPServerAction()

  const handleServerAction = async (action: 'start' | 'stop' | 'restart') => {
    if (!name) return
    setActionPending(true)
    try {
      await serverAction.mutateAsync({
        name,
        request: { action },
      })
      setTimeout(() => refetch(), 1000)
    } catch (error) {
      console.error('Server action failed:', error)
    } finally {
      setActionPending(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!server) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <p className="text-muted-foreground">服务器不存在</p>
        <button
          onClick={() => navigate('/mcp')}
          className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          返回列表
        </button>
      </div>
    )
  }

  const isRunning = server.status === 'running'

  const tabs: { key: TabType; label: string; icon: React.ReactNode }[] = [
    { key: 'info', label: '简介', icon: <Info className="h-4 w-4" /> },
    { key: 'tools', label: '工具列表', icon: <Wrench className="h-4 w-4" /> },
    { key: 'config', label: '配置方式', icon: <Settings className="h-4 w-4" /> },
  ]

  return (
    <div className="space-y-6">
      {/* 顶部导航 */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/mcp')}
          className="inline-flex items-center justify-center w-8 h-8 rounded-md border bg-background hover:bg-accent"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-muted">
              <Server className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">{server.display_name}</h1>
              <p className="text-sm text-muted-foreground">{server.name}</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isRunning ? (
            <>
              <button
                onClick={() => handleServerAction('stop')}
                disabled={actionPending}
                title="停止"
                className="inline-flex items-center justify-center w-9 h-9 rounded-md border bg-background hover:bg-accent disabled:opacity-50"
              >
                {actionPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Square className="h-4 w-4" />}
              </button>
              <button
                onClick={() => handleServerAction('restart')}
                disabled={actionPending}
                title="重启"
                className="inline-flex items-center justify-center w-9 h-9 rounded-md border bg-background hover:bg-accent disabled:opacity-50"
              >
                {actionPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              </button>
            </>
          ) : (
            <button
              onClick={() => handleServerAction('start')}
              disabled={actionPending}
              title="启动"
              className="inline-flex items-center justify-center w-9 h-9 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {actionPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            </button>
          )}
          <button
            onClick={() => refetch()}
            title="刷新"
            className="inline-flex items-center justify-center w-9 h-9 rounded-md border bg-background hover:bg-accent"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Tab 导航 */}
      <div className="border-b">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                'flex items-center gap-2 px-1 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
                activeTab === tab.key
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab 内容 */}
      <div>
        {activeTab === 'info' && <InfoTab server={server} />}
        {activeTab === 'tools' && <ToolsTab serverName={server.name} />}
        {activeTab === 'config' && <ConfigTab server={server} />}
      </div>
    </div>
  )
}

export default Component
