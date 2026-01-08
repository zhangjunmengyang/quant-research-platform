#!/usr/bin/env python3
"""
MCP 服务和工具发现脚本

快速列出所有 MCP 服务器及其支持的工具。

用法:
    python scripts/list_mcp_tools.py           # 列出所有服务和工具
    python scripts/list_mcp_tools.py --json    # JSON 格式输出
    python scripts/list_mcp_tools.py --summary # 仅显示摘要
    python scripts/list_mcp_tools.py --server factor-hub  # 指定服务器
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from typing import Optional

import httpx

# MCP 服务器配置
MCP_SERVERS = {
    "factor-hub": {"port": 6789, "description": "因子知识库"},
    "data-hub": {"port": 6790, "description": "数据层"},
    "strategy-hub": {"port": 6791, "description": "策略知识库"},
    "note-hub": {"port": 6792, "description": "笔记知识库"},
}

BASE_HOST = "http://localhost"


@dataclass
class ToolInfo:
    """工具信息"""

    name: str
    description: str
    input_schema: dict


@dataclass
class ServerInfo:
    """服务器信息"""

    name: str
    port: int
    description: str
    online: bool
    version: Optional[str] = None
    tools: list[ToolInfo] = None
    error: Optional[str] = None


async def check_server_health(client: httpx.AsyncClient, server_name: str, port: int) -> tuple[bool, Optional[str]]:
    """检查服务器健康状态"""
    try:
        resp = await client.get(f"{BASE_HOST}:{port}/health", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            return True, data.get("version", "unknown")
        return False, None
    except Exception:
        return False, None


async def get_server_tools(client: httpx.AsyncClient, port: int) -> list[ToolInfo]:
    """通过 MCP 协议获取工具列表"""
    tools = []
    mcp_url = f"{BASE_HOST}:{port}/mcp/"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        # 步骤 1: 初始化 MCP 连接
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mcp-discovery", "version": "1.0.0"},
            },
        }

        resp = await client.post(mcp_url, json=init_request, headers=headers, timeout=10.0)
        if resp.status_code != 200:
            return tools

        # 步骤 2: 获取工具列表
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        resp = await client.post(mcp_url, json=list_request, headers=headers, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            if "result" in data and "tools" in data["result"]:
                for tool in data["result"]["tools"]:
                    tools.append(
                        ToolInfo(
                            name=tool.get("name", ""),
                            description=tool.get("description", ""),
                            input_schema=tool.get("inputSchema", {}),
                        )
                    )
    except Exception:
        # 静默失败，返回空列表
        pass

    return tools


async def discover_servers(server_filter: Optional[str] = None) -> list[ServerInfo]:
    """发现所有 MCP 服务器"""
    servers = []

    async with httpx.AsyncClient() as client:
        tasks = []

        for name, config in MCP_SERVERS.items():
            if server_filter and name != server_filter:
                continue

            async def check_server(name=name, config=config):
                port = config["port"]
                online, version = await check_server_health(client, name, port)

                server_info = ServerInfo(
                    name=name,
                    port=port,
                    description=config["description"],
                    online=online,
                    version=version,
                    tools=[],
                )

                if online:
                    server_info.tools = await get_server_tools(client, port)

                return server_info

            tasks.append(check_server())

        servers = await asyncio.gather(*tasks)

    return sorted(servers, key=lambda s: s.port)


def print_summary(servers: list[ServerInfo]) -> None:
    """打印摘要"""
    print("\n" + "=" * 60)
    print("MCP 服务发现摘要")
    print("=" * 60)

    online_count = sum(1 for s in servers if s.online)
    total_tools = sum(len(s.tools) for s in servers if s.online)

    print(f"\n服务器: {online_count}/{len(servers)} 在线")
    print(f"工具总数: {total_tools}")

    print("\n服务器状态:")
    print("-" * 60)
    for server in servers:
        status = "[在线]" if server.online else "[离线]"
        tool_count = len(server.tools) if server.tools else 0
        print(f"  {status} {server.name:<15} :{server.port}  ({server.description}, {tool_count} 工具)")

    print()


def print_detailed(servers: list[ServerInfo]) -> None:
    """打印 Markdown 表格格式"""
    online_count = sum(1 for s in servers if s.online)
    total_tools = sum(len(s.tools) for s in servers if s.online)

    print(f"\n# MCP 服务和工具列表\n")
    print(f"服务器: {online_count}/{len(servers)} 在线 | 工具总数: {total_tools}\n")

    # 表头
    print("| Server | Tool | Description |")
    print("|--------|------|-------------|")

    for server in servers:
        if not server.online:
            print(f"| {server.name} (:{server.port}) | - | *服务离线* |")
            continue

        if not server.tools:
            print(f"| {server.name} (:{server.port}) | - | *无工具* |")
            continue

        # 第一行显示服务器名
        first_tool = True
        for tool in sorted(server.tools, key=lambda t: t.name):
            # 处理描述：取第一行，截断过长内容
            desc = tool.description.split("\n")[0].strip()
            if len(desc) > 50:
                desc = desc[:47] + "..."

            if first_tool:
                server_cell = f"{server.name} (:{server.port})"
                first_tool = False
            else:
                server_cell = ""

            print(f"| {server_cell} | `{tool.name}` | {desc} |")

    print()


def print_json(servers: list[ServerInfo]) -> None:
    """JSON 格式输出"""
    output = {
        "servers": [
            {
                "name": s.name,
                "port": s.port,
                "description": s.description,
                "online": s.online,
                "version": s.version,
                "tools": (
                    [{"name": t.name, "description": t.description, "inputSchema": t.input_schema} for t in s.tools]
                    if s.tools
                    else []
                ),
            }
            for s in servers
        ],
        "summary": {
            "total_servers": len(servers),
            "online_servers": sum(1 for s in servers if s.online),
            "total_tools": sum(len(s.tools) for s in servers if s.online),
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


async def main():
    parser = argparse.ArgumentParser(description="MCP 服务和工具发现脚本")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--summary", action="store_true", help="仅显示摘要")
    parser.add_argument("--server", type=str, help="指定服务器名称")

    args = parser.parse_args()

    # 验证服务器名称
    if args.server and args.server not in MCP_SERVERS:
        print(f"错误: 未知的服务器 '{args.server}'")
        print(f"可用的服务器: {', '.join(MCP_SERVERS.keys())}")
        sys.exit(1)

    # 发现服务器
    servers = await discover_servers(args.server)

    # 输出
    if args.json:
        print_json(servers)
    elif args.summary:
        print_summary(servers)
    else:
        print_detailed(servers)


if __name__ == "__main__":
    asyncio.run(main())
