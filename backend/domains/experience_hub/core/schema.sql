-- ============================================
-- Experience Hub 数据库表结构
-- ============================================
--
-- 存储研究经验的结构化信息，支持:
-- - PARL 框架的经验内容
-- - 三级分类（strategic/tactical/operational）
-- - 生命周期管理（draft/validated/deprecated）
-- - 向量检索（pgvector HNSW）
-- - 关联其他实体
--
-- 依赖:
-- - PostgreSQL 14+
-- - pgvector 扩展（用于向量检索）
-- ============================================

-- 启用 pgvector 扩展（如果尚未启用）
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 经验主表
-- ============================================

CREATE TABLE IF NOT EXISTS experiences (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) NOT NULL UNIQUE,

    -- 基础信息
    title VARCHAR(500) NOT NULL,
    experience_level VARCHAR(20) NOT NULL DEFAULT 'operational',
    category VARCHAR(50) DEFAULT '',

    -- 核心内容（PARL 框架，JSONB 存储）
    -- {problem, approach, result, lesson}
    content JSONB NOT NULL DEFAULT '{}',

    -- 上下文信息（JSONB 存储）
    -- {market_regime, factor_styles, time_horizon, asset_class, tags}
    context JSONB NOT NULL DEFAULT '{}',

    -- 来源追溯
    source_type VARCHAR(20) DEFAULT 'manual',
    source_ref VARCHAR(500) DEFAULT '',

    -- 置信度与验证
    confidence DECIMAL(3, 2) DEFAULT 0.50,
    validation_count INTEGER DEFAULT 0,
    last_validated TIMESTAMP,

    -- 生命周期
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    deprecated_reason TEXT DEFAULT '',

    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 约束
    CONSTRAINT experiences_level_check CHECK (
        experience_level IN ('strategic', 'tactical', 'operational')
    ),
    CONSTRAINT experiences_status_check CHECK (
        status IN ('draft', 'validated', 'deprecated')
    ),
    CONSTRAINT experiences_source_type_check CHECK (
        source_type IN ('research', 'backtest', 'live_trade', 'external', 'manual', 'curated')
    ),
    CONSTRAINT experiences_confidence_check CHECK (
        confidence >= 0 AND confidence <= 1
    )
);

-- 经验表索引
CREATE INDEX IF NOT EXISTS idx_experiences_uuid ON experiences(uuid);
CREATE INDEX IF NOT EXISTS idx_experiences_level ON experiences(experience_level);
CREATE INDEX IF NOT EXISTS idx_experiences_category ON experiences(category);
CREATE INDEX IF NOT EXISTS idx_experiences_status ON experiences(status);
CREATE INDEX IF NOT EXISTS idx_experiences_source ON experiences(source_type, source_ref);
CREATE INDEX IF NOT EXISTS idx_experiences_confidence ON experiences(confidence);
CREATE INDEX IF NOT EXISTS idx_experiences_created_at ON experiences(created_at);
CREATE INDEX IF NOT EXISTS idx_experiences_updated_at ON experiences(updated_at);

-- JSONB 索引（用于上下文查询）
CREATE INDEX IF NOT EXISTS idx_experiences_context_gin ON experiences USING GIN (context);
CREATE INDEX IF NOT EXISTS idx_experiences_content_gin ON experiences USING GIN (content);

-- 全文搜索索引
CREATE INDEX IF NOT EXISTS idx_experiences_title_trgm ON experiences USING GIN (title gin_trgm_ops);

-- ============================================
-- 经验关联表
-- ============================================

CREATE TABLE IF NOT EXISTS experience_links (
    id SERIAL PRIMARY KEY,
    experience_id INTEGER NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    experience_uuid VARCHAR(36) NOT NULL,

    -- 关联实体
    entity_type VARCHAR(20) NOT NULL,
    entity_id VARCHAR(500) NOT NULL,

    -- 关系类型
    relation VARCHAR(50) NOT NULL DEFAULT 'related',

    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 约束
    CONSTRAINT experience_links_entity_type_check CHECK (
        entity_type IN ('factor', 'strategy', 'note', 'research', 'experience')
    ),
    CONSTRAINT experience_links_unique UNIQUE (experience_id, entity_type, entity_id, relation)
);

-- 关联表索引
CREATE INDEX IF NOT EXISTS idx_experience_links_experience_id ON experience_links(experience_id);
CREATE INDEX IF NOT EXISTS idx_experience_links_entity ON experience_links(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_experience_links_relation ON experience_links(relation);

-- ============================================
-- 经验向量表（pgvector）
-- ============================================

CREATE TABLE IF NOT EXISTS experience_embeddings (
    id SERIAL PRIMARY KEY,
    experience_id INTEGER NOT NULL UNIQUE REFERENCES experiences(id) ON DELETE CASCADE,

    -- 向量（维度根据实际模型调整，默认 1536 for OpenAI）
    embedding vector(1536) NOT NULL,

    -- 模型信息
    model VARCHAR(100) DEFAULT '',

    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- HNSW 向量索引（用于近似最近邻搜索）
CREATE INDEX IF NOT EXISTS idx_experience_embeddings_hnsw ON experience_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 128);

-- ============================================
-- 经验提炼关系表
-- ============================================
-- 记录经验的提炼来源（从哪些经验提炼而来）

CREATE TABLE IF NOT EXISTS experience_curation_sources (
    id SERIAL PRIMARY KEY,
    curated_experience_id INTEGER NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    source_experience_id INTEGER NOT NULL REFERENCES experiences(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 约束
    CONSTRAINT experience_curation_unique UNIQUE (curated_experience_id, source_experience_id)
);

-- 提炼关系索引
CREATE INDEX IF NOT EXISTS idx_curation_curated ON experience_curation_sources(curated_experience_id);
CREATE INDEX IF NOT EXISTS idx_curation_source ON experience_curation_sources(source_experience_id);

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
COMMENT ON COLUMN experiences.experience_level IS '经验层级: strategic(战略级), tactical(战术级), operational(操作级)';
COMMENT ON COLUMN experiences.content IS 'PARL 框架内容: {problem, approach, result, lesson}';
COMMENT ON COLUMN experiences.context IS '上下文信息: {market_regime, factor_styles, time_horizon, asset_class, tags}';
COMMENT ON COLUMN experiences.status IS '生命周期状态: draft(草稿), validated(已验证), deprecated(已废弃)';
COMMENT ON COLUMN experiences.confidence IS '置信度 0-1，随验证次数增加';

COMMENT ON TABLE experience_links IS '经验关联表，建立经验与其他实体的关系';
COMMENT ON COLUMN experience_links.entity_type IS '关联实体类型: factor, strategy, note, research, experience';
COMMENT ON COLUMN experience_links.relation IS '关系类型: related(相关), derived_from(派生自), applied_to(应用于), curated_from(提炼自)';

COMMENT ON TABLE experience_embeddings IS '经验向量表，存储用于语义检索的向量';
COMMENT ON COLUMN experience_embeddings.embedding IS '向量表示，使用 pgvector 存储';

COMMENT ON TABLE experience_curation_sources IS '经验提炼来源表，记录高层经验的来源经验';
