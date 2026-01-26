def __getattr__(name: str):
    if name in ('NoteHubMCPServer', 'create_note_hub_config', 'run_server'):
        from .server import NoteHubMCPServer, create_note_hub_config, run_server
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
