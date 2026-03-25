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

    -- 层次信息
    heading_path TEXT DEFAULT '',          -- 标题路径，JSON 数组格式
    section_title VARCHAR(500) DEFAULT '', -- 所属章节标题

    -- 嵌入信息
    embedding_model VARCHAR(100) DEFAULT '',  -- 使用的嵌入模型
    embedding vector(1536),                   -- 稠密向量（1536 维，text-embedding-3-small）

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
