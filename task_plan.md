# Task Plan: Migrate linked_note_id to Edge System

## Goal
Remove redundant `linked_note_id` field from note system, fully migrate to Edge system for entity relations.

## Context
- Edge system (`mcp_core/edge/`) already implemented with `link_note`, `get_note_edges`, `trace_note_lineage`
- `linked_note_id` is redundant - verification->hypothesis relation should use Edge system
- 25 files currently reference `linked_note_id`

## Phases

### Phase 1: Backend Core Models
- [ ] `backend/domains/note_hub/core/models.py` - Remove `linked_note_id` from Note dataclass
- [ ] `backend/domains/note_hub/core/store.py` - Remove `linked_note_id` from store operations
- [ ] `backend/domains/note_hub/core/__init__.py` - Update docstring if needed

### Phase 2: Backend Services
- [ ] `backend/domains/note_hub/services/note_service.py` - Remove `linked_note_id` from create_note, update docstrings
- [ ] `backend/domains/note_hub/__init__.py` - Update module docstring

### Phase 3: Backend API Layer
- [ ] `backend/app/schemas/note.py` - Remove `linked_note_id` from schemas
- [ ] `backend/app/routes/v1/notes.py` - Remove `linked_note_id` from routes, update verification endpoint

### Phase 4: MCP Tools
- [ ] `backend/domains/note_hub/api/mcp/tools/note_tools.py` - Remove `linked_note_id` from tools
- [ ] `backend/domains/note_hub/api/mcp/server.py` - Update docstring if needed

### Phase 5: Sync Layer
- [ ] `backend/domains/mcp_core/sync/note_sync.py` - Remove `linked_note_id` from sync

### Phase 6: Database
- [ ] `docker/compose/init.sql` - Remove `linked_note_id` column from notes table

### Phase 7: Frontend
- [ ] `frontend/src/features/note/types.ts` - Remove `linked_note_id` from types
- [ ] `frontend/src/features/note/api.ts` - Update API calls if needed
- [ ] `frontend/src/features/note/hooks.ts` - Update hooks if needed
- [ ] `frontend/src/pages/notes/Detail.tsx` - Remove `linked_note_id` usage
- [ ] `frontend/src/pages/notes/List.tsx` - Remove `linked_note_id` usage if any

### Phase 8: Documentation
- [ ] `docs/architecture/knowledge-experience-system.md` - Update documentation

### Phase 9: Data Migration
- [ ] Migrate existing `linked_note_id` relations to Edge system (if needed)
- [ ] Clean up verification markdown files with `linked_note_id` in frontmatter

## Decisions
| Decision | Rationale |
|----------|-----------|
| Use Edge system for all relations | Single source of truth, supports any entity type |
| Verification->Hypothesis uses `verifies` relation | Semantic clarity |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (none yet) | | |
