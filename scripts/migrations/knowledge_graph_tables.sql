-- 知识图谱表结构
-- 用于存储实体、关系和支持语义搜索
--
-- 执行方式：
-- psql -h localhost -U postgres -d quant_research -f knowledge_graph_tables.sql

-- 启用 pgvector 扩展（如果尚未启用）
CREATE EXTENSION IF NOT EXISTS vector;

-- ==================== 实体表 ====================
CREATE TABLE IF NOT EXISTS kg_entities (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- factor, strategy, market_regime, concept, metric, time_window, asset, parameter, condition, action
    name VARCHAR(255) NOT NULL,
    properties JSONB DEFAULT '{}',
    embedding vector(1536),  -- OpenAI text-embedding-3-small 维度
    source_type VARCHAR(20) DEFAULT 'manual',  -- manual, llm_extracted, imported
    source_ref TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 同名同类型实体唯一约束
    CONSTRAINT uq_entity_type_name UNIQUE (entity_type, name)
);

-- 实体表索引
CREATE INDEX IF NOT EXISTS idx_kg_entities_uuid ON kg_entities(uuid);
CREATE INDEX IF NOT EXISTS idx_kg_entities_type ON kg_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_kg_entities_name ON kg_entities(name);
CREATE INDEX IF NOT EXISTS idx_kg_entities_source_type ON kg_entities(source_type);
CREATE INDEX IF NOT EXISTS idx_kg_entities_created_at ON kg_entities(created_at);

-- 实体名称文本搜索索引
CREATE INDEX IF NOT EXISTS idx_kg_entities_name_gin ON kg_entities USING gin(name gin_trgm_ops);

-- 实体向量索引（HNSW 用于近似最近邻搜索）
-- 注意：需要先有数据后再创建索引效果更好
CREATE INDEX IF NOT EXISTS idx_kg_entities_embedding ON kg_entities
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 实体表注释
COMMENT ON TABLE kg_entities IS '知识图谱实体表';
COMMENT ON COLUMN kg_entities.uuid IS '实体唯一标识符';
COMMENT ON COLUMN kg_entities.entity_type IS '实体类型: factor, strategy, market_regime, concept, metric, time_window, asset, parameter, condition, action';
COMMENT ON COLUMN kg_entities.name IS '实体名称';
COMMENT ON COLUMN kg_entities.properties IS '扩展属性（JSONB）';
COMMENT ON COLUMN kg_entities.embedding IS '向量嵌入（用于语义搜索）';
COMMENT ON COLUMN kg_entities.source_type IS '来源类型: manual(手动), llm_extracted(LLM抽取), imported(导入)';
COMMENT ON COLUMN kg_entities.source_ref IS '来源引用';


-- ==================== 关系表 ====================
CREATE TABLE IF NOT EXISTS kg_relations (
    id SERIAL PRIMARY KEY,
    relation_type VARCHAR(50) NOT NULL,  -- related_to, derived_from, belongs_to, effective_in, ...
    source_id INTEGER NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    target_id INTEGER NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    source_uuid VARCHAR(36),
    target_uuid VARCHAR(36),
    properties JSONB DEFAULT '{}',
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 同类型关系唯一约束（防止重复关系）
    CONSTRAINT uq_relation UNIQUE (source_id, target_id, relation_type)
);

-- 关系表索引
CREATE INDEX IF NOT EXISTS idx_kg_relations_type ON kg_relations(relation_type);
CREATE INDEX IF NOT EXISTS idx_kg_relations_source ON kg_relations(source_id);
CREATE INDEX IF NOT EXISTS idx_kg_relations_target ON kg_relations(target_id);
CREATE INDEX IF NOT EXISTS idx_kg_relations_source_uuid ON kg_relations(source_uuid);
CREATE INDEX IF NOT EXISTS idx_kg_relations_target_uuid ON kg_relations(target_uuid);
CREATE INDEX IF NOT EXISTS idx_kg_relations_created_at ON kg_relations(created_at);

-- 复合索引（图遍历优化）
CREATE INDEX IF NOT EXISTS idx_kg_relations_source_type ON kg_relations(source_id, relation_type);
CREATE INDEX IF NOT EXISTS idx_kg_relations_target_type ON kg_relations(target_id, relation_type);

-- 关系表注释
COMMENT ON TABLE kg_relations IS '知识图谱关系表';
COMMENT ON COLUMN kg_relations.relation_type IS '关系类型: related_to, derived_from, belongs_to, effective_in, conflicts_with, optimized_by, composed_of, outperforms_in, causes, indicates, precedes, follows, has_parameter, sensitive_to, applies_to, requires';
COMMENT ON COLUMN kg_relations.source_id IS '源实体 ID';
COMMENT ON COLUMN kg_relations.target_id IS '目标实体 ID';
COMMENT ON COLUMN kg_relations.properties IS '关系属性（JSONB）';
COMMENT ON COLUMN kg_relations.weight IS '关系权重（0-1）';


-- ==================== 启用 pg_trgm 扩展（用于模糊搜索）====================
CREATE EXTENSION IF NOT EXISTS pg_trgm;


-- ==================== 验证迁移 ====================
DO $$
BEGIN
    -- 验证 kg_entities 表
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'kg_entities'
    ) THEN
        RAISE NOTICE 'Migration successful: kg_entities table exists';
    ELSE
        RAISE EXCEPTION 'Migration failed: kg_entities table not found';
    END IF;

    -- 验证 kg_relations 表
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'kg_relations'
    ) THEN
        RAISE NOTICE 'Migration successful: kg_relations table exists';
    ELSE
        RAISE EXCEPTION 'Migration failed: kg_relations table not found';
    END IF;

    -- 验证向量扩展
    IF EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'vector'
    ) THEN
        RAISE NOTICE 'Migration successful: pgvector extension enabled';
    ELSE
        RAISE WARNING 'Warning: pgvector extension not enabled, vector search will not work';
    END IF;
END $$;
