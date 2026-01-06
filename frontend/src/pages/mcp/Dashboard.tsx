/**
 * MCP Dashboard Page
 * MCP 服务管理仪表盘
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Server,
  Play,
  Square,
  RefreshCw,
  Loader2,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useMCPDashboard,
  useMCPServerAction,
  useMCPStartAll,
} from '@/features/mcp'
import type {
  MCPServerInfo,
  MCPServerStatus,
} from '@/features/mcp'

// 状态灯颜色配置
const STATUS_LIGHT: Record<MCPServerStatus, { color: string; glow: string }> = {
  running: {
    color: 'bg-green-500',
    glow: 'shadow-[0_0_8px_2px_rgba(34,197,94,0.6)]',
  },
  stopped: {
    color: 'bg-red-500',
    glow: 'shadow-[0_0_8px_2px_rgba(239,68,68,0.6)]',
  },
  error: {
    color: 'bg-orange-500',
    glow: 'shadow-[0_0_8px_2px_rgba(249,115,22,0.6)]',
  },
  starting: {
    color: 'bg-yellow-500',
    glow: 'shadow-[0_0_8px_2px_rgba(234,179,8,0.6)]',
  },
  stopping: {
    color: 'bg-yellow-500',
    glow: 'shadow-[0_0_8px_2px_rgba(234,179,8,0.6)]',
  },
  unresponsive: {
    color: 'bg-amber-500',
    glow: 'shadow-[0_0_8px_2px_rgba(245,158,11,0.6)]',
  },
}

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
function StatusLight({ status }: { status: MCPServerStatus }) {
  const config = STATUS_LIGHT[status] || STATUS_LIGHT.stopped
  // running 状态缓慢闪烁，starting/stopping/unresponsive 状态快速闪烁
  const shouldAnimate = status === 'running' || status === 'starting' || status === 'stopping' || status === 'unresponsive'
  const animationClass = status === 'running' ? 'animate-[pulse_3s_ease-in-out_infinite]' : 'animate-pulse'

  return (
    <div
      className={cn(
        'w-2 h-2 rounded-full',
        config.color,
        config.glow,
        shouldAnimate && animationClass
      )}
    />
  )
}

// 服务器卡片组件
function ServerCard({
  server,
  displayStatus,
  onAction,
  isActionPending,
  onClick,
}: {
  server: MCPServerInfo
  displayStatus: MCPServerStatus
  onAction: (action: 'start' | 'stop' | 'restart', e: React.MouseEvent) => void
  isActionPending: boolean
  onClick: () => void
}) {
  const isRunning = displayStatus === 'running'
  const isStarting = displayStatus === 'starting'
  const isUnresponsive = displayStatus === 'unresponsive'

  return (
    <div
      className="rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden relative cursor-pointer hover:border-primary/50 transition-colors group"
      onClick={onClick}
    >
      {/* 右上角状态灯 */}
      <div className="absolute top-4 right-4">
        <StatusLight status={displayStatus} />
      </div>

      {/* 卡片内容 */}
      <div className="p-4 pr-10">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-muted">
            <Server className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-medium truncate">{server.display_name}</h3>
            <p className="text-sm text-muted-foreground truncate">{server.description}</p>
          </div>
        </div>

        {/* 错误信息 */}
        {server.error_message && (
          <div className="mt-2 px-2 py-1 rounded bg-amber-50 text-amber-700 text-xs">
            {server.error_message}
          </div>
        )}

        {/* 统计信息 */}
        <div className="mt-4 grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-lg font-semibold">{server.tools_count}</div>
            <div className="text-xs text-muted-foreground">工具</div>
          </div>
          <div>
            <div className="text-lg font-semibold">{server.port}</div>
            <div className="text-xs text-muted-foreground">端口</div>
          </div>
          <div>
            <div className="text-lg font-semibold">
              {formatUptime(server.uptime_seconds)}
            </div>
            <div className="text-xs text-muted-foreground">时长</div>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="mt-4 flex items-center justify-between">
          <div className="flex gap-2">
            {isRunning ? (
              <>
                <button
                  onClick={(e) => onAction('stop', e)}
                  disabled={isActionPending}
                  title="停止"
                  className="inline-flex items-center justify-center w-8 h-8 rounded-md border bg-background hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isActionPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Square className="h-4 w-4 text-red-500" />
                  )}
                </button>
                <button
                  onClick={(e) => onAction('restart', e)}
                  disabled={isActionPending}
                  title="重启"
                  className="inline-flex items-center justify-center w-8 h-8 rounded-md border bg-background hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isActionPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                </button>
              </>
            ) : isStarting ? (
              // 启动中状态：显示加载动画，禁用按钮
              <button
                disabled
                title="启动中..."
                className="inline-flex items-center justify-center w-8 h-8 rounded-md border bg-background opacity-50 cursor-not-allowed"
              >
                <Loader2 className="h-4 w-4 animate-spin text-yellow-500" />
              </button>
            ) : isUnresponsive ? (
              // 卡死状态：显示重启按钮（会先清理再启动）
              <button
                onClick={(e) => onAction('start', e)}
                disabled={isActionPending}
                title="重启服务（自动清理卡死进程）"
                className="inline-flex items-center justify-center w-8 h-8 rounded-md border bg-background hover:bg-amber-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isActionPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4 text-amber-500" />
                )}
              </button>
            ) : (
              <button
                onClick={(e) => onAction('start', e)}
                disabled={isActionPending}
                title="启动"
                className="inline-flex items-center justify-center w-8 h-8 rounded-md border bg-background hover:bg-green-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isActionPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4 text-green-500" />
                )}
              </button>
            )}
          </div>

          {/* 查看详情 */}
          <div className="flex items-center gap-1 text-sm text-muted-foreground group-hover:text-primary transition-colors">
            <span>详情</span>
            <ChevronRight className="h-4 w-4" />
          </div>
        </div>
      </div>
    </div>
  )
}

// 主页面组件
export function Component() {
  const navigate = useNavigate()
  const [actionPending, setActionPending] = useState<string | null>(null)
  // 跟踪正在启动中的服务器，用于显示 starting 状态
  const [startingServers, setStartingServers] = useState<Set<string>>(new Set())
  const [startAllPending, setStartAllPending] = useState(false)

  const { data: dashboard, isLoading, refetch } = useMCPDashboard()
  const serverAction = useMCPServerAction()
  const startAll = useMCPStartAll()

  const handleServerAction = async (
    serverName: string,
    action: 'start' | 'stop' | 'restart',
    e: React.MouseEvent
  ) => {
    e.stopPropagation()
    setActionPending(serverName)

    // 如果是启动操作，立即标记为 starting 状态
    if (action === 'start' || action === 'restart') {
      setStartingServers(prev => new Set(prev).add(serverName))
    }

    try {
      await serverAction.mutateAsync({
        name: serverName,
        request: { action },
      })
      setTimeout(() => {
        refetch()
      }, 1000)
    } catch (error) {
      console.error('Server action failed:', error)
    } finally {
      setActionPending(null)
      // 清除 starting 状态
      setStartingServers(prev => {
        const next = new Set(prev)
        next.delete(serverName)
        return next
      })
    }
  }

  const handleStartAll = async () => {
    setStartAllPending(true)
    // 将所有未运行的服务器标记为 starting
    const stoppedServers = dashboard?.servers
      .filter(s => s.status === 'stopped' || s.status === 'error')
      .map(s => s.name) || []
    setStartingServers(new Set(stoppedServers))

    try {
      await startAll.mutateAsync()
      setTimeout(() => {
        refetch()
      }, 1000)
    } catch (error) {
      console.error('Start all failed:', error)
    } finally {
      setStartAllPending(false)
      setStartingServers(new Set())
    }
  }

  const handleCardClick = (serverName: string) => {
    navigate(`/mcp/${serverName}`)
  }

  // 计算服务器的显示状态（考虑本地 starting 状态）
  const getDisplayStatus = (server: MCPServerInfo): MCPServerStatus => {
    if (startingServers.has(server.name)) {
      return 'starting'
    }
    return server.status
  }

  // 检查是否有未运行的服务器
  const hasStoppedServers = dashboard?.servers.some(
    s => s.status === 'stopped' || s.status === 'error'
  )

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 服务器列表 */}
      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold">服务器列表</h3>
            <span className="text-sm text-muted-foreground">
              {dashboard?.running_servers || 0}/{dashboard?.total_servers || 0} 运行中
            </span>
          </div>
          <div className="flex items-center gap-2">
            {/* 一键启动按钮 */}
            {hasStoppedServers && (
              <button
                onClick={handleStartAll}
                disabled={startAllPending}
                title="启动全部"
                className="inline-flex items-center justify-center gap-1.5 px-3 h-8 rounded-md border bg-background hover:bg-green-50 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
              >
                {startAllPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4 text-green-500" />
                )}
                <span>启动全部</span>
              </button>
            )}
            <button
              onClick={() => refetch()}
              title="刷新"
              className="inline-flex items-center justify-center w-8 h-8 rounded-md border bg-background hover:bg-accent"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {dashboard?.servers.map((server) => (
            <ServerCard
              key={server.name}
              server={server}
              displayStatus={getDisplayStatus(server)}
              onAction={(action, e) => handleServerAction(server.name, action, e)}
              isActionPending={actionPending === server.name}
              onClick={() => handleCardClick(server.name)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export default Component
