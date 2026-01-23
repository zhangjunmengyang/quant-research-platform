def __getattr__(name: str):
    if name in ('ExperienceHubMCPServer', 'create_experience_hub_config', 'run_server'):
        from .server import ExperienceHubMCPServer, create_experience_hub_config, run_server
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
