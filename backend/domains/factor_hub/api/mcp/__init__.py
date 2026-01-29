def __getattr__(name: str):
    if name in ('FactorHubMCPServer', 'create_mcp_server', 'run_server', 'create_factor_hub_config'):
        from .server import (
            FactorHubMCPServer,
            create_factor_hub_config,
            create_mcp_server,
            run_server,
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
