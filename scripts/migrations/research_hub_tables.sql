-- ============================================
-- Research Hub 数据表
-- 研报知识库相关表结构
-- ============================================

-- 研报表
CREATE TABLE IF NOT EXISTS research_reports (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL,

    -- 基本信息
    title VARCHAR(500) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT DEFAULT '',
    file_size INTEGER DEFAULT 0,
    page_count INTEGER DEFAULT 0,

    -- 元数据
    author VARCHAR(255) DEFAULT '',
    source_url TEXT DEFAULT '',
    publish_date DATE,

    -- 内容
    content_markdown TEXT DEFAULT '',  -- 解析后的 Markdown 全文
    summary TEXT DEFAULT '',           -- 自动生成的摘要
    tags VARCHAR(500) DEFAULT '',      -- 逗号分隔的标签
    category VARCHAR(100) DEFAULT '',  -- 研报分类

    -- 处理状态
    -- uploaded -> parsing -> chunking -> embedding -> indexing -> ready
    -- 任何阶段失败 -> failed
    status VARCHAR(20) DEFAULT 'uploaded',
    progress INTEGER DEFAULT 0,        -- 处理进度 0-100
    error_message TEXT DEFAULT '',     -- 错误信息

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parsed_at TIMESTAMP,               -- 解析完成时间
    indexed_at TIMESTAMP               -- 索引完成时间
);

-- 研报索引
CREATE INDEX IF NOT EXISTS idx_research_reports_uuid ON research_reports(uuid);
CREATE INDEX IF NOT EXISTS idx_research_reports_status ON research_reports(status);
CREATE INDEX IF NOT EXISTS idx_research_reports_category ON research_reports(category);
CREATE INDEX IF NOT EXISTS idx_research_reports_created_at ON research_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_reports_tags ON research_reports(tags);

-- 研报全文搜索索引
CREATE INDEX IF NOT EXISTS idx_research_reports_search ON research_reports
USING GIN(to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(summary, '')));

-- 更新时间触发器
CREATE TRIGGER update_research_reports_updated_at
    BEFORE UPDATE ON research_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================
-- 研报切块表
-- ============================================

CREATE TABLE IF NOT EXISTS research_chunks (
    id SERIAL PRIMARY KEY,
    chunk_id VARCHAR(36) UNIQUE NOT NULL,  -- 切块唯一标识

    -- 关联研报
    report_id INTEGER NOT NULL REFERENCES research_reports(id) ON DELETE CASCADE,
    report_uuid VARCHAR(36) NOT NULL,

    -- 位置信息
    chunk_index INTEGER NOT NULL,          -- 在文档中的序号
    page_start INTEGER,                    -- 起始页
    page_end INTEGER,                      -- 结束页

    -- 内容信息
    chunk_type VARCHAR(20) DEFAULT 'text', -- text/table/formula/figure/code
    content TEXT NOT NULL,                 -- 切块内容
    token_count INTEGER DEFAULT 0,         -- Token 数量

    -- 层次信息（用于 TreeRAG 扩展）
    heading_path TEXT DEFAULT '',          -- 标题路径，JSON 数组格式
    section_title VARCHAR(500) DEFAULT '', -- 所属章节标题

    -- 嵌入信息
    embedding_model VARCHAR(100) DEFAULT '',  -- 使用的嵌入模型
    embedding vector(512),                    -- 稠密向量（512 维，bge-small-zh）

    -- 扩展元数据
    metadata JSONB DEFAULT '{}',

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 切块索引
CREATE INDEX IF NOT EXISTS idx_research_chunks_chunk_id ON research_chunks(chunk_id);
CREATE INDEX IF NOT EXISTS idx_research_chunks_report_id ON research_chunks(report_id);
CREATE INDEX IF NOT EXISTS idx_research_chunks_report_uuid ON research_chunks(report_uuid);
CREATE INDEX IF NOT EXISTS idx_research_chunks_type ON research_chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_research_chunks_index ON research_chunks(report_id, chunk_index);

-- 切块向量索引（HNSW 算法）
CREATE INDEX IF NOT EXISTS idx_research_chunks_embedding ON research_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 切块全文搜索索引（用于混合检索）
CREATE INDEX IF NOT EXISTS idx_research_chunks_content_search ON research_chunks
USING GIN(to_tsvector('simple', content));

-- 切块元数据索引
CREATE INDEX IF NOT EXISTS idx_research_chunks_metadata ON research_chunks USING GIN(metadata);


-- ============================================
-- 研报对话表
-- ============================================

CREATE TABLE IF NOT EXISTS research_conversations (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL,

    -- 对话信息
    title VARCHAR(500) DEFAULT '',         -- 对话标题（自动生成）
    report_id INTEGER REFERENCES research_reports(id) ON DELETE SET NULL,  -- 可选关联研报

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 对话索引
CREATE INDEX IF NOT EXISTS idx_research_conversations_uuid ON research_conversations(uuid);
CREATE INDEX IF NOT EXISTS idx_research_conversations_report_id ON research_conversations(report_id);
CREATE INDEX IF NOT EXISTS idx_research_conversations_updated_at ON research_conversations(updated_at DESC);

-- 更新时间触发器
CREATE TRIGGER update_research_conversations_updated_at
    BEFORE UPDATE ON research_conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================
-- 研报对话消息表
-- ============================================

CREATE TABLE IF NOT EXISTS research_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES research_conversations(id) ON DELETE CASCADE,

    -- 消息内容
    role VARCHAR(20) NOT NULL,             -- user/assistant/system
    content TEXT NOT NULL,

    -- 来源引用（JSON 数组）
    -- [{chunk_id, report_id, content_preview, score}]
    sources JSONB DEFAULT '[]',

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 消息索引
CREATE INDEX IF NOT EXISTS idx_research_messages_conversation_id ON research_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_research_messages_created_at ON research_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_research_messages_role ON research_messages(role);


-- ============================================
-- RAG 流水线配置表（用于 A/B 测试）
-- ============================================

CREATE TABLE IF NOT EXISTS rag_pipeline_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,     -- 配置名称
    description TEXT DEFAULT '',

    -- 组件配置（JSON）
    -- {
    --   "parser": {"type": "mineru", "model": "MinerU2.5"},
    --   "chunker": {"type": "recursive", "chunk_size": 512, "overlap": 50},
    --   "embedder": {"type": "bge_m3", "model": "BAAI/bge-m3"},
    --   "retriever": {"type": "hybrid", "top_k": 20},
    --   "reranker": {"type": "bge_reranker", "top_k": 5},
    --   "generator": {"type": "openai", "model": "gpt-4"}
    -- }
    config JSONB NOT NULL DEFAULT '{}',

    -- 状态
    is_active BOOLEAN DEFAULT FALSE,       -- 是否为当前激活配置
    is_default BOOLEAN DEFAULT FALSE,      -- 是否为默认配置

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 配置索引
CREATE INDEX IF NOT EXISTS idx_rag_pipeline_configs_name ON rag_pipeline_configs(name);
CREATE INDEX IF NOT EXISTS idx_rag_pipeline_configs_active ON rag_pipeline_configs(is_active);

-- 更新时间触发器
CREATE TRIGGER update_rag_pipeline_configs_updated_at
    BEFORE UPDATE ON rag_pipeline_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 插入默认配置
INSERT INTO rag_pipeline_configs (name, description, config, is_active, is_default) VALUES
('default', '默认 RAG 配置', '{
    "parser": {"type": "mineru", "version": "2.5"},
    "chunker": {"type": "recursive", "chunk_size": 512, "chunk_overlap": 50},
    "embedder": {"type": "bge_m3", "model": "BAAI/bge-m3", "dimensions": 1024},
    "retriever": {"type": "dense", "top_k": 20},
    "reranker": {"type": "bge_reranker", "model": "BAAI/bge-reranker-v2-m3", "top_k": 5},
    "generator": {"type": "openai", "model": "gpt-4o-mini"}
}', TRUE, TRUE)
ON CONFLICT (name) DO NOTHING;


-- ============================================
-- RAG 评估记录表（用于对比实验）
-- ============================================

CREATE TABLE IF NOT EXISTS rag_evaluations (
    id SERIAL PRIMARY KEY,

    -- 关联信息
    pipeline_config_id INTEGER REFERENCES rag_pipeline_configs(id) ON DELETE SET NULL,
    pipeline_name VARCHAR(100) NOT NULL,

    -- 评估查询
    query TEXT NOT NULL,
    expected_answer TEXT DEFAULT '',       -- 可选的预期答案

    -- 检索结果
    retrieved_chunks JSONB DEFAULT '[]',   -- 检索到的切块
    retrieval_top_k INTEGER,
    rerank_top_k INTEGER,

    -- 生成结果
    generated_answer TEXT DEFAULT '',

    -- 评估指标
    -- RAGAS 指标
    faithfulness FLOAT,                    -- 忠实度
    answer_relevance FLOAT,                -- 答案相关性
    context_precision FLOAT,               -- 上下文精确度
    context_recall FLOAT,                  -- 上下文召回率

    -- 检索指标
    recall_at_k FLOAT,
    precision_at_k FLOAT,
    ndcg FLOAT,
    mrr FLOAT,                             -- Mean Reciprocal Rank

    -- 延迟指标（毫秒）
    retrieval_latency_ms INTEGER,
    rerank_latency_ms INTEGER,
    generation_latency_ms INTEGER,
    total_latency_ms INTEGER,

    -- 元数据
    metadata JSONB DEFAULT '{}',

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 评估索引
CREATE INDEX IF NOT EXISTS idx_rag_evaluations_pipeline ON rag_evaluations(pipeline_config_id);
CREATE INDEX IF NOT EXISTS idx_rag_evaluations_name ON rag_evaluations(pipeline_name);
CREATE INDEX IF NOT EXISTS idx_rag_evaluations_created_at ON rag_evaluations(created_at DESC);
