/**
 * MCP management API client
 */

import { apiClient, type ApiResponse } from '@/lib/api/client'
import type {
  MCPServerInfo,
  MCPServerStats,
  MCPToolInfo,
  MCPToolCallRequest,
  MCPToolCallResult,
  MCPServerActionRequest,
  MCPServerActionResult,
  MCPDashboardStats,
} from './types'

const BASE_URL = '/mcp-management'

export const mcpApi = {
  /**
   * Get all MCP servers status
   */
  listServers: async (): Promise<MCPServerInfo[]> => {
    const { data } = await apiClient.get<ApiResponse<MCPServerInfo[]>>(`${BASE_URL}/servers`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch MCP servers')
    }
    return data.data
  },

  /**
   * Get specific MCP server status
   */
  getServer: async (name: string): Promise<MCPServerInfo> => {
    const { data } = await apiClient.get<ApiResponse<MCPServerInfo>>(`${BASE_URL}/servers/${name}`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Server not found')
    }
    return data.data
  },

  /**
   * Get MCP server statistics
   */
  getServerStats: async (name: string): Promise<MCPServerStats> => {
    const { data } = await apiClient.get<ApiResponse<MCPServerStats>>(
      `${BASE_URL}/servers/${name}/stats`
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch server stats')
    }
    return data.data
  },

  /**
   * Perform server action (start/stop/restart)
   */
  serverAction: async (
    name: string,
    request: MCPServerActionRequest
  ): Promise<MCPServerActionResult> => {
    const { data } = await apiClient.post<ApiResponse<MCPServerActionResult>>(
      `${BASE_URL}/servers/${name}/action`,
      request
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to perform server action')
    }
    return data.data
  },

  /**
   * Get all tools from all servers
   */
  listAllTools: async (): Promise<MCPToolInfo[]> => {
    const { data } = await apiClient.get<ApiResponse<MCPToolInfo[]>>(`${BASE_URL}/tools`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch tools')
    }
    return data.data
  },

  /**
   * Get tools from specific server
   */
  getServerTools: async (name: string): Promise<MCPToolInfo[]> => {
    const { data } = await apiClient.get<ApiResponse<MCPToolInfo[]>>(
      `${BASE_URL}/servers/${name}/tools`
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch server tools')
    }
    return data.data
  },

  /**
   * Call MCP tool
   */
  callTool: async (request: MCPToolCallRequest): Promise<MCPToolCallResult> => {
    const { data } = await apiClient.post<ApiResponse<MCPToolCallResult>>(
      `${BASE_URL}/tools/call`,
      request,
      { timeout: 120000 } // 2 minutes for tool execution
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to call tool')
    }
    return data.data
  },

  /**
   * Get dashboard statistics
   */
  getDashboardStats: async (): Promise<MCPDashboardStats> => {
    const { data } = await apiClient.get<ApiResponse<MCPDashboardStats>>(`${BASE_URL}/dashboard`)
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to fetch dashboard stats')
    }
    return data.data
  },

  /**
   * Start all stopped servers
   */
  startAllServers: async (): Promise<MCPServerActionResult[]> => {
    const { data } = await apiClient.post<ApiResponse<MCPServerActionResult[]>>(
      `${BASE_URL}/servers/start-all`,
      {},
      { timeout: 60000 } // 60 seconds for starting all servers
    )
    if (!data.success || !data.data) {
      throw new Error(data.error || 'Failed to start all servers')
    }
    return data.data
  },
}
