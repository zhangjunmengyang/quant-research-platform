/**
 * MCP management React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { mcpApi } from './api'
import type { MCPServerActionRequest, MCPToolCallRequest } from './types'

// Query Keys
export const mcpKeys = {
  all: ['mcp'] as const,
  servers: () => [...mcpKeys.all, 'servers'] as const,
  server: (name: string) => [...mcpKeys.servers(), name] as const,
  serverStats: (name: string) => [...mcpKeys.server(name), 'stats'] as const,
  tools: () => [...mcpKeys.all, 'tools'] as const,
  serverTools: (name: string) => [...mcpKeys.tools(), name] as const,
  dashboard: () => [...mcpKeys.all, 'dashboard'] as const,
}

// 默认缓存时间
const DEFAULT_STALE_TIME = 30 * 1000 // 30 秒（MCP 状态更新较频繁）

/**
 * Hook to fetch all MCP servers status
 */
export function useMCPServers() {
  return useQuery({
    queryKey: mcpKeys.servers(),
    queryFn: mcpApi.listServers,
    staleTime: DEFAULT_STALE_TIME,
    refetchInterval: 30000, // 30 秒刷新一次，减少请求频率
  })
}

/**
 * Hook to fetch specific MCP server status
 */
export function useMCPServer(name: string) {
  return useQuery({
    queryKey: mcpKeys.server(name),
    queryFn: () => mcpApi.getServer(name),
    enabled: !!name,
    staleTime: 15 * 1000, // 15 秒缓存
    refetchInterval: 15000, // 15 秒刷新一次
  })
}

/**
 * Hook to fetch MCP server statistics
 */
export function useMCPServerStats(name: string) {
  return useQuery({
    queryKey: mcpKeys.serverStats(name),
    queryFn: () => mcpApi.getServerStats(name),
    enabled: !!name,
    staleTime: 15 * 1000,
    refetchInterval: 15000, // 15 秒刷新一次
  })
}

/**
 * Hook to fetch all tools from all servers
 */
export function useMCPTools() {
  return useQuery({
    queryKey: mcpKeys.tools(),
    queryFn: mcpApi.listAllTools,
    staleTime: 5 * 60 * 1000, // 工具列表很少变化，5 分钟缓存
  })
}

/**
 * Hook to fetch tools from specific server
 */
export function useMCPServerTools(name: string) {
  return useQuery({
    queryKey: mcpKeys.serverTools(name),
    queryFn: () => mcpApi.getServerTools(name),
    enabled: !!name,
    staleTime: 5 * 60 * 1000, // 工具列表很少变化
  })
}

/**
 * Hook to fetch dashboard statistics
 */
export function useMCPDashboard() {
  return useQuery({
    queryKey: mcpKeys.dashboard(),
    queryFn: mcpApi.getDashboardStats,
    staleTime: DEFAULT_STALE_TIME, // 30 秒缓存 - 进入页面时立即显示缓存数据
    refetchInterval: 30000, // 30 秒刷新一次
  })
}

/**
 * Hook for server actions (start/stop/restart)
 */
export function useMCPServerAction() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ name, request }: { name: string; request: MCPServerActionRequest }) =>
      mcpApi.serverAction(name, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.all })
    },
  })
}

/**
 * Hook for calling MCP tools
 */
export function useMCPToolCall() {
  return useMutation({
    mutationFn: (request: MCPToolCallRequest) => mcpApi.callTool(request),
  })
}

/**
 * Hook for starting all servers at once
 */
export function useMCPStartAll() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => mcpApi.startAllServers(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: mcpKeys.all })
    },
  })
}
