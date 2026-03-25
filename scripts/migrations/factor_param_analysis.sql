-- 因子参数分析字段迁移
-- 为因子表添加 param_analysis 字段，存储参数敏感性分析结果

-- 添加 param_analysis 字段 (TEXT 类型，存储 JSON)
ALTER TABLE factors ADD COLUMN IF NOT EXISTS param_analysis TEXT DEFAULT '';

-- 添加注释
COMMENT ON COLUMN factors.param_analysis IS '参数分析结果 (JSON): 包含参数遍历结果、最优参数、ECharts 配置等';
