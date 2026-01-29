-- ============================================
-- Experience Hub 数据库表结构
-- ============================================
--
-- 存储研究经验的结构化信息，支持:
-- - PARL 框架的经验内容
-- - 基于标签的分类管理
-- - 关联其他实体
--
-- 依赖:
-- - PostgreSQL 14+
-- ============================================

-- ============================================
-- 经验主表
-- ============================================

CREATE TABLE IF NOT EXISTS experiences (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) NOT NULL UNIQUE,

    -- 基础信息
    title VARCHAR(500) NOT NULL,

    -- 核心内容（PARL 框架，JSONB 存储）
    -- {problem, approach, result, lesson}
    content JSONB NOT NULL DEFAULT '{}',

    -- 上下文信息（JSONB 存储，包含标签）
    -- {tags, factor_styles, market_regime, time_horizon, asset_class}
    context JSONB NOT NULL DEFAULT '{}',

    -- 来源追溯
    source_type VARCHAR(20) DEFAULT 'manual',
    source_ref VARCHAR(500) DEFAULT '',

    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 约束
    CONSTRAINT experiences_source_type_check CHECK (
        source_type IN ('research', 'backtest', 'live_trade', 'external', 'manual')
    )
);

-- 经验表索引
CREATE INDEX IF NOT EXISTS idx_experiences_uuid ON experiences(uuid);
CREATE INDEX IF NOT EXISTS idx_experiences_source ON experiences(source_type, source_ref);
CREATE INDEX IF NOT EXISTS idx_experiences_created_at ON experiences(created_at);
CREATE INDEX IF NOT EXISTS idx_experiences_updated_at ON experiences(updated_at);

-- JSONB 索引（用于标签和上下文查询）
CREATE INDEX IF NOT EXISTS idx_experiences_context_gin ON experiences USING GIN (context);
CREATE INDEX IF NOT EXISTS idx_experiences_content_gin ON experiences USING GIN (content);

-- 全文搜索索引
CREATE INDEX IF NOT EXISTS idx_experiences_title_trgm ON experiences USING GIN (title gin_trgm_ops);

-- ============================================
-- [已删除] experience_links 表已迁移至 Neo4j (graph-hub)
-- 参见: private/docs/architecture/tasks/graph-migration.md
-- ============================================

-- ============================================
-- 触发器: 自动更新 updated_at
-- ============================================

CREATE OR REPLACE FUNCTION update_experiences_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_experiences_updated_at ON experiences;
CREATE TRIGGER trigger_experiences_updated_at
    BEFORE UPDATE ON experiences
    FOR EACH ROW
    EXECUTE FUNCTION update_experiences_updated_at();

-- ============================================
-- 注释
-- ============================================

COMMENT ON TABLE experiences IS '经验知识库主表，存储结构化的研究经验';
COMMENT ON COLUMN experiences.content IS 'PARL 框架内容: {problem, approach, result, lesson}';
COMMENT ON COLUMN experiences.context IS '上下文信息: {tags, factor_styles, market_regime, time_horizon, asset_class}';
