# Findings: 实时双向同步

## Requirements
- 策略回测完成后立即同步到 private/strategies/
- 因子元数据更新后立即同步到 private/factors/metadata/
- 笔记创建/更新后立即同步到 private/notes/
- 经验创建/更新后立即同步到 private/experiences/

## Research Findings

### 当前同步状态
| 数据类型 | export_single() | 实时同步触发 |
|---------|-----------------|-------------|
| 因子代码 | N/A | 已实现（FactorService.create_factor） |
| 因子元数据 | 已有 | 未触发 |
| 策略 | 缺失 | 未实现 |
| 笔记 | 缺失 | 未实现 |
| 经验 | 缺失 | 未实现 |

### 关键文件位置
| 模块 | SyncService | Store |
|------|-------------|-------|
| 策略 | sync/strategy_sync.py | strategy_hub/services/strategy_store.py |
| 因子 | sync/factor_sync.py | factor_hub/core/store.py |
| 笔记 | sync/note_sync.py | note_hub/core/store.py |
| 经验 | sync/experience_sync.py | experience_hub/core/store.py |

### Store 方法签名
| Store | add() 返回值 | update() 签名 | 标识字段 |
|-------|-------------|--------------|---------|
| StrategyStore | Strategy 对象 | update(strategy: Strategy) | id (UUID) |
| FactorStore | bool | update(filename, **fields) | filename |
| NoteStore | Optional[int] | update(note_id, **fields) | id, uuid |
| ExperienceStore | Optional[int] | update(exp_id, **fields) | id, uuid |

### 现有基础设施
- `BaseSyncService` 提供 write_yaml_atomic(), write_json_atomic() 等原子写入方法
- `lock.py` 提供 sync_lock() 文件锁机制
- `SyncManager` 管理批量同步，但无单条同步接口

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 创建 SyncTrigger 单例 | 统一接口，延迟初始化，避免循环导入 |
| 在 Store 层触发同步 | 保证所有数据变更都会触发，不遗漏 |
| 同步执行而非异步 | 写入耗时短（<10ms），避免复杂性 |

## Resources
- `backend/domains/mcp_core/sync/factor_sync.py:211-236` - export_single 参考实现
- `backend/domains/mcp_core/sync/base.py` - BaseSyncService 基类
- `backend/domains/mcp_core/sync/lock.py` - 文件锁机制
