def __getattr__(name: str):
    if name in ('StrategyHubMCPServer', 'create_mcp_server', 'run_server', 'create_strategy_hub_config'):
        from .server import (
            StrategyHubMCPServer,
            create_mcp_server,
            create_strategy_hub_config,
            run_server,
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
