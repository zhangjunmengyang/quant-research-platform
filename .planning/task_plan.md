# Task Plan: 实时双向同步

## Goal
所有数据（策略、因子元数据、笔记、经验）在数据库更新后立即同步到 private 目录，实现像因子代码一样的实时双向同步。

## Current Phase
Phase 1

## Phases

### Phase 1: 需求分析与代码探索
- [x] 理解当前同步机制
- [x] 识别需要添加 export_single() 的 SyncService
- [x] 识别需要触发同步的 Store 位置
- **Status:** complete

### Phase 2: 基础设施
- [ ] 创建 SyncTrigger 模块 (trigger.py)
- [ ] 更新 sync/__init__.py 导出
- **Status:** pending

### Phase 3: SyncService 扩展
- [ ] StrategySyncService 添加 export_single()
- [ ] NoteSyncService 添加 export_single()
- [ ] ExperienceSyncService 添加 export_single()
- **Status:** pending

### Phase 4: Store 层集成
- [ ] StrategyStore.add()/update() 触发同步
- [ ] FactorStore.update() 触发元数据同步
- [ ] NoteStore.add()/update() 触发同步
- [ ] ExperienceStore.add()/update() 触发同步
- **Status:** pending

### Phase 5: 测试验证
- [ ] 启动服务测试
- [ ] 验证各类型数据同步
- **Status:** pending

## Key Questions
1. 同步是否需要异步执行？ -> 不需要，写入耗时很短
2. 同步失败如何处理？ -> Fire-and-forget，记录日志，不影响主业务

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Store 层直接调用同步 | 简单直接，项目规模适中 |
| 同步执行（非异步） | 写入耗时短，保证数据一致性 |
| Fire-and-forget 模式 | 同步失败不影响主业务 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (暂无) | | |

## Notes
- FactorSyncService 已有 export_single()，其他三个需要新增
- 参考 FactorSyncService 的实现模式
