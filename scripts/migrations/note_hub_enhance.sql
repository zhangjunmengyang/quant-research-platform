-- Note Hub 增强迁移
-- 将 note-hub 重构为"研究草稿/临时记录"层
--
-- 新增字段：
-- - note_type: 笔记类型（observation/hypothesis/finding/trail/general）
-- - research_session_id: 研究会话 ID，用于追踪研究轨迹
-- - promoted_to_experience_id: 已提炼为经验的 ID
-- - is_archived: 是否已归档
--
-- 执行方式：
-- psql -h localhost -U postgres -d quant_research -f note_hub_enhance.sql

-- 添加新字段
ALTER TABLE notes ADD COLUMN IF NOT EXISTS note_type VARCHAR(20) DEFAULT 'general';
ALTER TABLE notes ADD COLUMN IF NOT EXISTS research_session_id VARCHAR(36);
ALTER TABLE notes ADD COLUMN IF NOT EXISTS promoted_to_experience_id INTEGER;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_notes_note_type ON notes(note_type);
CREATE INDEX IF NOT EXISTS idx_notes_research_session_id ON notes(research_session_id);
CREATE INDEX IF NOT EXISTS idx_notes_is_archived ON notes(is_archived);
CREATE INDEX IF NOT EXISTS idx_notes_promoted ON notes(promoted_to_experience_id) WHERE promoted_to_experience_id IS NOT NULL;

-- 复合索引（常用查询优化）
-- 按类型和归档状态查询
CREATE INDEX IF NOT EXISTS idx_notes_type_archived ON notes(note_type, is_archived);
-- 按研究会话和创建时间查询（研究轨迹）
CREATE INDEX IF NOT EXISTS idx_notes_session_created ON notes(research_session_id, created_at) WHERE research_session_id IS NOT NULL;

-- 添加注释
COMMENT ON COLUMN notes.note_type IS '笔记类型: observation(观察), hypothesis(假设), finding(发现), trail(轨迹), general(通用)';
COMMENT ON COLUMN notes.research_session_id IS '研究会话 ID，用于追踪同一研究过程中的多条笔记';
COMMENT ON COLUMN notes.promoted_to_experience_id IS '已提炼为经验的 ID，如果不为空则表示该笔记已提炼为正式经验';
COMMENT ON COLUMN notes.is_archived IS '是否已归档，归档后默认不显示在列表中';

-- 验证迁移
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'notes' AND column_name = 'note_type'
    ) THEN
        RAISE NOTICE 'Migration successful: note_type column exists';
    ELSE
        RAISE EXCEPTION 'Migration failed: note_type column not found';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'notes' AND column_name = 'research_session_id'
    ) THEN
        RAISE NOTICE 'Migration successful: research_session_id column exists';
    ELSE
        RAISE EXCEPTION 'Migration failed: research_session_id column not found';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'notes' AND column_name = 'is_archived'
    ) THEN
        RAISE NOTICE 'Migration successful: is_archived column exists';
    ELSE
        RAISE EXCEPTION 'Migration failed: is_archived column not found';
    END IF;
END $$;
