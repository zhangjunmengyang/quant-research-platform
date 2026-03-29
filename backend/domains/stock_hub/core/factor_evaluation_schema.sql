-- Factor Evaluation Library 数据库表结构
-- PostgreSQL 14+

CREATE TABLE IF NOT EXISTS factor_evaluations (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) NOT NULL UNIQUE,
    factor_name VARCHAR(200) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content JSONB NOT NULL DEFAULT '{}',
    tags JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_factor_evaluations_uuid ON factor_evaluations(uuid);
CREATE INDEX IF NOT EXISTS idx_factor_evaluations_factor_name ON factor_evaluations(factor_name);
CREATE INDEX IF NOT EXISTS idx_factor_evaluations_created_at ON factor_evaluations(created_at);
CREATE INDEX IF NOT EXISTS idx_factor_evaluations_tags_gin ON factor_evaluations USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_factor_evaluations_content_gin ON factor_evaluations USING GIN (content);

-- Trigger: auto-update updated_at
CREATE OR REPLACE FUNCTION update_factor_evaluations_updated_at()
RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = CURRENT_TIMESTAMP; RETURN NEW; END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_factor_evaluations_updated_at ON factor_evaluations;
CREATE TRIGGER trigger_factor_evaluations_updated_at
    BEFORE UPDATE ON factor_evaluations
    FOR EACH ROW
    EXECUTE FUNCTION update_factor_evaluations_updated_at();

-- Comments
COMMENT ON TABLE factor_evaluations IS '因子评估库，保存因子分析结果和 AI 评估文本';
COMMENT ON COLUMN factor_evaluations.content IS '{evaluations: {eval_type: text}, analysis_snapshot: {...}}';
COMMENT ON COLUMN factor_evaluations.tags IS '标签数组，用于分类筛选';
