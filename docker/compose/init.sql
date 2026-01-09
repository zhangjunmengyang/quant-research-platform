-- PostgreSQL 初始化脚本
-- 创建扩展和基础表结构

-- 启用 pgvector 扩展（向量检索）
CREATE EXTENSION IF NOT EXISTS vector;

-- 因子表
CREATE TABLE IF NOT EXISTS factors (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    uuid VARCHAR(36) DEFAULT '',
    factor_type VARCHAR(20) DEFAULT 'time_series',

    -- 基础字段
    style VARCHAR(255) DEFAULT '',
    formula TEXT DEFAULT '',
    input_data TEXT DEFAULT '',
    value_range TEXT DEFAULT '',
    description TEXT DEFAULT '',
    analysis TEXT DEFAULT '',

    -- 代码相关
    code_path TEXT DEFAULT '',
    code_content TEXT DEFAULT '',
    code_complexity FLOAT,

    -- 评分和验证
    llm_score FLOAT,
    verified BOOLEAN DEFAULT FALSE,
    verify_note TEXT DEFAULT '',

    -- 排除状态
    excluded BOOLEAN DEFAULT FALSE,
    exclude_reason TEXT DEFAULT '',

    -- IC 指标
    ic FLOAT,
    rank_ic FLOAT,

    -- 回测指标
    backtest_sharpe FLOAT,
    backtest_ic FLOAT,
    backtest_ir FLOAT,
    turnover FLOAT,
    decay INTEGER,

    -- 分类标签
    market_regime TEXT DEFAULT '',
    best_holding_period INTEGER,
    tags TEXT DEFAULT '',

    -- 向量嵌入（用于语义检索）
    embedding vector(1536),

    -- 时间戳
    last_backtest_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_factors_style ON factors(style);
CREATE INDEX IF NOT EXISTS idx_factors_score ON factors(llm_score);
CREATE INDEX IF NOT EXISTS idx_factors_verified ON factors(verified);
CREATE INDEX IF NOT EXISTS idx_factors_uuid ON factors(uuid);
CREATE INDEX IF NOT EXISTS idx_factors_factor_type ON factors(factor_type);
CREATE INDEX IF NOT EXISTS idx_factors_excluded ON factors(excluded);
CREATE INDEX IF NOT EXISTS idx_factors_tags ON factors(tags);

-- 向量索引（HNSW 算法，用于近似最近邻搜索）
CREATE INDEX IF NOT EXISTS idx_factors_embedding ON factors
USING hnsw (embedding vector_cosine_ops);

-- 全文搜索索引
CREATE INDEX IF NOT EXISTS idx_factors_search ON factors
USING GIN(to_tsvector('simple', coalesce(filename, '') || ' ' || coalesce(description, '') || ' ' || coalesce(analysis, '')));

-- 回测结果表
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,

    -- 策略配置（完整快照，可重现）
    strategy_config JSONB NOT NULL,

    -- 核心指标
    total_return FLOAT,
    annual_return FLOAT,
    sharpe_ratio FLOAT,
    max_drawdown FLOAT,
    win_rate FLOAT,
    trade_count INTEGER,

    -- 扩展指标
    metrics JSONB DEFAULT '{}',

    -- 时间范围
    start_date DATE,
    end_date DATE,

    -- 状态
    status VARCHAR(20) DEFAULT 'completed',
    error_message TEXT,

    -- 元信息
    runtime_seconds FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 回测结果索引
CREATE INDEX IF NOT EXISTS idx_backtest_status ON backtest_results(status);
CREATE INDEX IF NOT EXISTS idx_backtest_date ON backtest_results(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backtest_config ON backtest_results USING GIN(strategy_config);

-- 任务队列表（用于 PostgreSQL 原生队列，可选）
CREATE TABLE IF NOT EXISTS task_queue (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(36) UNIQUE NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    params JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    result JSONB,
    error TEXT,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_task_status ON task_queue(status);
CREATE INDEX IF NOT EXISTS idx_task_type ON task_queue(task_type);
CREATE INDEX IF NOT EXISTS idx_task_priority ON task_queue(priority DESC, created_at ASC);

-- 更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_factors_updated_at
    BEFORE UPDATE ON factors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 经验概览表（研究草稿/临时记录层）
CREATE TABLE IF NOT EXISTS notes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT DEFAULT '',
    tags VARCHAR(500) DEFAULT '',
    source VARCHAR(50) DEFAULT '',
    source_ref VARCHAR(255) DEFAULT '',

    -- 笔记类型：observation(观察), hypothesis(假设), finding(发现), trail(轨迹), general(通用)
    note_type VARCHAR(20) DEFAULT 'general',
    -- 研究会话 ID，用于追踪同一研究过程中的多条笔记
    research_session_id VARCHAR(36),
    -- 已提炼为经验的 ID
    promoted_to_experience_id INTEGER,
    -- 是否已归档
    is_archived BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 笔记索引
CREATE INDEX IF NOT EXISTS idx_notes_tags ON notes(tags);
CREATE INDEX IF NOT EXISTS idx_notes_source ON notes(source);
CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_note_type ON notes(note_type);
CREATE INDEX IF NOT EXISTS idx_notes_research_session_id ON notes(research_session_id);
CREATE INDEX IF NOT EXISTS idx_notes_is_archived ON notes(is_archived);
CREATE INDEX IF NOT EXISTS idx_notes_promoted ON notes(promoted_to_experience_id) WHERE promoted_to_experience_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_notes_type_archived ON notes(note_type, is_archived);
CREATE INDEX IF NOT EXISTS idx_notes_session_created ON notes(research_session_id, created_at) WHERE research_session_id IS NOT NULL;

-- 笔记全文搜索索引
CREATE INDEX IF NOT EXISTS idx_notes_search ON notes
USING GIN(to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, '')));

-- 笔记更新时间触发器
CREATE TRIGGER update_notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 日志存储表
-- ============================================

-- 日志主题表
CREATE TABLE IF NOT EXISTS log_topics (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    -- 该主题的字段定义 (JSON Schema 格式)
    field_schema JSONB DEFAULT '{}',
    -- 保留天数，超过后自动清理
    retention_days INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 预定义日志主题（3个核心主题）
INSERT INTO log_topics (name, display_name, description, field_schema, retention_days) VALUES
('llm', 'LLM 调用', '系统内部 LLM 调用日志（字段填充、Review 等）', '{
    "properties": {
        "call_id": {"type": "string", "description": "调用唯一标识"},
        "workflow": {"type": "string", "description": "流程类型: fill/review"},
        "factor_name": {"type": "string", "description": "因子名称"},
        "field": {"type": "string", "description": "字段名称: style/formula/description/analysis/llm_score"},
        "model": {"type": "string", "description": "模型名称"},
        "provider": {"type": "string", "description": "服务提供商"},
        "system_prompt": {"type": "string", "description": "系统提示词（完整）"},
        "user_prompt": {"type": "string", "description": "用户提示词（完整）"},
        "response_content": {"type": "string", "description": "模型响应内容（完整）"},
        "status": {"type": "string", "enum": ["success", "failed"]},
        "duration_ms": {"type": "number", "description": "执行耗时(ms)"},
        "input_tokens": {"type": "integer", "description": "输入token数"},
        "output_tokens": {"type": "integer", "description": "输出token数"},
        "total_tokens": {"type": "integer", "description": "总token数"},
        "cost": {"type": "number", "description": "预估成本(USD)"},
        "error_message": {"type": "string", "description": "错误信息"}
    }
}', 30),
('mcp', 'MCP 调用', '外部 MCP 协议调用日志（工具调用、资源访问）', '{
    "properties": {
        "tool_name": {"type": "string", "description": "工具名称"},
        "mcp_server": {"type": "string", "description": "MCP 服务名"},
        "method": {"type": "string", "description": "MCP 方法"},
        "status": {"type": "string", "enum": ["success", "error"]},
        "duration_ms": {"type": "number", "description": "执行耗时(ms)"},
        "error": {"type": "string", "description": "错误信息"}
    }
}', 30),
('system', '系统日志', '通用系统日志（启动、错误、业务事件等）', '{
    "properties": {
        "component": {"type": "string", "description": "组件名称"},
        "action": {"type": "string", "description": "操作类型"},
        "service": {"type": "string", "description": "服务名称"}
    }
}', 7)
ON CONFLICT (name) DO NOTHING;

-- 日志条目表（使用 JSONB 存储灵活的日志数据）
CREATE TABLE IF NOT EXISTS logs (
    id BIGSERIAL PRIMARY KEY,
    -- 时间戳（纳秒精度）
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- 关联的主题
    topic_id INTEGER NOT NULL REFERENCES log_topics(id) ON DELETE CASCADE,
    -- 日志级别: debug, info, warning, error
    level VARCHAR(10) NOT NULL DEFAULT 'info',
    -- 服务名称
    service VARCHAR(100) NOT NULL,
    -- 日志器名称
    logger VARCHAR(200) DEFAULT '',
    -- 追踪 ID（用于关联同一请求的多条日志）
    trace_id VARCHAR(64) DEFAULT '',
    -- 日志消息（简短描述）
    message TEXT NOT NULL,
    -- 扩展数据（JSONB 格式，包含所有额外字段）
    data JSONB DEFAULT '{}',
    -- 原始日志行（可选，用于调试）
    raw_line TEXT DEFAULT ''
);

-- 日志表索引
-- 时间范围查询（最常用）
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC);
-- 按主题+时间查询
CREATE INDEX IF NOT EXISTS idx_logs_topic_timestamp ON logs(topic_id, timestamp DESC);
-- 按服务+时间查询
CREATE INDEX IF NOT EXISTS idx_logs_service_timestamp ON logs(service, timestamp DESC);
-- 按级别+时间查询（用于筛选错误）
CREATE INDEX IF NOT EXISTS idx_logs_level_timestamp ON logs(level, timestamp DESC);
-- 按 trace_id 查询（追踪完整请求链路）
CREATE INDEX IF NOT EXISTS idx_logs_trace_id ON logs(trace_id) WHERE trace_id != '';
-- JSONB 数据索引（用于字段筛选）
CREATE INDEX IF NOT EXISTS idx_logs_data ON logs USING GIN(data jsonb_path_ops);
-- 全文搜索索引
CREATE INDEX IF NOT EXISTS idx_logs_message_search ON logs USING GIN(to_tsvector('simple', message));

-- 分区表（按月分区，提高查询性能和数据清理效率）
-- 注意：PostgreSQL 12+ 支持声明式分区
-- 如果需要分区，可以将 logs 表改为分区表

-- 日志清理函数
CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
    topic_record RECORD;
BEGIN
    FOR topic_record IN SELECT id, retention_days FROM log_topics LOOP
        DELETE FROM logs
        WHERE topic_id = topic_record.id
        AND timestamp < NOW() - (topic_record.retention_days || ' days')::INTERVAL;
        deleted_count := deleted_count + ROW_COUNT;
    END LOOP;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 可以设置定时任务调用 cleanup_old_logs()，例如使用 pg_cron 扩展

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
    embedding vector(1024),                   -- 稠密向量（预留 1024 维，BGE-M3）

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
