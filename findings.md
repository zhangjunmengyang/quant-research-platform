# Findings: Edge System Migration

## Current State

### Files with linked_note_id (25 files)
```
Backend:
- backend/domains/note_hub/core/models.py
- backend/domains/note_hub/core/store.py
- backend/domains/note_hub/core/__init__.py
- backend/domains/note_hub/services/note_service.py
- backend/domains/note_hub/__init__.py
- backend/domains/note_hub/api/mcp/server.py
- backend/domains/note_hub/api/mcp/tools/note_tools.py
- backend/domains/mcp_core/sync/note_sync.py
- backend/app/schemas/note.py
- backend/app/routes/v1/notes.py

Database:
- docker/compose/init.sql

Frontend:
- frontend/src/features/note/types.ts
- frontend/src/features/note/api.ts
- frontend/src/features/note/hooks.ts
- frontend/src/pages/notes/Detail.tsx
- frontend/src/pages/notes/List.tsx

Docs:
- docs/architecture/knowledge-experience-system.md

Data Files (verification notes with linked_note_id in frontmatter):
- private/notes/verifications/*.md (10+ files)
```

### Edge System Already Supports
- `link_note(note_id, target_type, target_id, relation)` - Create any relation
- `get_note_edges(note_id)` - Get all relations for a note
- `trace_note_lineage(note_id, direction, max_depth)` - Trace knowledge path

### Relation Types Available
- `derived_from` - Note derived from data/factor/strategy
- `verifies` - Verification verifies hypothesis
- `references` - Note references research
- `summarizes` - Experience summarizes notes
- `has_tag` - Entity has tag
- `related` - General relation

## Key Insight
`linked_note_id` was a shortcut for verification->hypothesis relation.
Edge system provides the same with:
```python
link_note(
    note_id=verification_id,
    target_type="note",
    target_id=str(hypothesis_id),
    relation="verifies"
)
```

## Migration Strategy
1. Remove field from all layers (model -> store -> service -> api -> frontend)
2. Update verification markdown files to remove `linked_note_id` from frontmatter
3. Existing relations can be migrated via Edge system if needed
