def __getattr__(name: str):
    if name in ('DataHubMCPServer', 'MCPServer', 'create_mcp_server', 'run_server', 'create_data_hub_config'):
        from .server import (
            DataHubMCPServer,
            MCPServer,
            create_mcp_server,
            run_server,
            create_data_hub_config,
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
