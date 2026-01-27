-- Note UUID Migration
-- 为 notes 表添加 UUID 字段，用于跨环境唯一标识

-- 1. 添加 UUID 字段
ALTER TABLE notes ADD COLUMN IF NOT EXISTS uuid VARCHAR(36);

-- 2. 为现有记录生成 UUID
UPDATE notes SET uuid = gen_random_uuid()::text WHERE uuid IS NULL;

-- 3. 添加非空约束
ALTER TABLE notes ALTER COLUMN uuid SET NOT NULL;

-- 4. 创建唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_notes_uuid ON notes(uuid);

-- 5. 验证迁移结果
DO $$
DECLARE
    null_count INTEGER;
    total_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO null_count FROM notes WHERE uuid IS NULL;
    SELECT COUNT(*) INTO total_count FROM notes;

    IF null_count > 0 THEN
        RAISE EXCEPTION 'Migration failed: % records still have NULL uuid', null_count;
    END IF;

    RAISE NOTICE 'Migration successful: % notes now have UUID', total_count;
END $$;
