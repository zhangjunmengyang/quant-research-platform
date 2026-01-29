# Graph 数据迁移计划

## 概述

将 PostgreSQL 中的 `knowledge_edges` 和 `experience_links` 表数据迁移到 Neo4j，完成后删除旧表。

## 当前状态

| 表 | 记录数 | 数据分布 |
|----|--------|---------|
| knowledge_edges | 33 | factor->factor(22), note->factor(5), note->note(4), data->tag(2) |
| experience_links | 9 | experience->note(6), experience->factor(3) |

## 迁移步骤

### 阶段 1: 准备 (已完成)

- [x] Neo4j 容器配置 (docker-compose)
- [x] graph-hub MCP 服务器实现
- [x] GraphStore 核心模块
- [x] pg_compat 双写兼容层
- [x] 基础迁移脚本

### 阶段 2: 迁移执行

```bash
# 1. 确保 Neo4j 运行
docker ps | grep neo4j

# 2. 运行迁移
cd backend
python -m domains.graph_hub.tasks.migration

# 3. 验证迁移
python -c "from domains.graph_hub.tasks.migration import verify_migration; print(verify_migration())"
```

### 阶段 3: 验证

1. **数量验证**: 对比 PG 和 Neo4j 记录数
2. **抽样验证**: 随机抽取 10 条边，验证数据一致
3. **功能验证**: 使用 graph-hub 工具查询

```bash
# Neo4j 验证查询
MATCH ()-[r]->() RETURN type(r), count(r)
```

### 阶段 4: 清理

1. **删除 pg_compat 双写逻辑**
2. **删除 PostgreSQL 旧表**
3. **更新 init.sql**
4. **删除 mcp_core/edge 模块**

## 清理完成情况

### 已完成

- [x] `backend/domains/graph_hub/core/pg_compat.py` - 已删除
- [x] `backend/domains/graph_hub/services/graph_service.py` - 已移除 pg_compat 调用
- [x] `backend/domains/graph_hub/core/__init__.py` - 已移除 pg_compat 导出
- [x] `backend/domains/graph_hub/core/models.py` - 已内置类型定义
- [x] `backend/domains/mcp_core/edge/models.py` - 已改为兼容层 (从 graph_hub 导入)
- [x] `docker/compose/init.sql` - 已删除 knowledge_edges 表定义
- [x] `backend/domains/experience_hub/core/schema.sql` - 已删除 experience_links 表定义

### 保留 (兼容层)

```
backend/domains/mcp_core/edge/           # 保留为兼容层，类型从 graph_hub 导入
```

## 回滚方案

如果迁移失败，旧数据仍在 PostgreSQL 中：

```sql
-- 验证旧数据完整
SELECT COUNT(*) FROM knowledge_edges;
SELECT COUNT(*) FROM experience_links;
```

## 执行检查清单

- [x] Neo4j 容器运行正常
- [x] 运行迁移脚本
- [x] 验证 Neo4j 数据完整 (42条边: 36 DERIVED_FROM, 4 VERIFIES, 2 HAS_TAG)
- [x] 测试 graph-hub 工具功能
- [x] 删除 pg_compat.py
- [x] 更新 mcp_core/edge 为兼容层 (从 graph_hub 重新导出)
- [x] 更新 init.sql
- [ ] 提交代码变更
