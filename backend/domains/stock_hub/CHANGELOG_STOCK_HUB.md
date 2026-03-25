# Stock Hub 变更日志

## Phase 1 - 域骨架 + 因子查询服务

### 新增文件
- `domains/stock_hub/__init__.py` - 域入口
- `domains/stock_hub/config.py` - 配置（路径、端口、缓存）
- `domains/stock_hub/models/__init__.py`
- `domains/stock_hub/models/factor_meta.py` - 因子元数据Pydantic模型
- `domains/stock_hub/services/__init__.py`
- `domains/stock_hub/services/stock_factor_service.py` - 因子查询服务（AST扫描+缓存）
- `domains/stock_hub/tools/__init__.py`
- `domains/stock_hub/tools/base.py` - MCP工具基类（延迟加载stock_factor_service）
- `domains/stock_hub/tools/factor_query_tool.py` - 3个MCP工具（list/detail/refresh）
- `domains/stock_hub/api/__init__.py`
- `domains/stock_hub/api/mcp/__init__.py`
- `domains/stock_hub/api/mcp/server.py` - MCP服务器（端口6795）
- `domains/stock_hub/scripts/__init__.py`
- `domains/stock_hub/tests/__init__.py`
- `domains/stock_hub/tests/test_factor_service.py` - 因子服务测试（7个测试用例）
- `domains/stock_hub/cache/` - 缓存目录（自动创建）

### 修改文件
无（Phase 1 不修改任何现有文件）

## Phase 2 - 回测执行服务

### 新增文件
- `domains/stock_hub/models/backtest_config_model.py` - 回测配置/结果Pydantic模型
- `domains/stock_hub/scripts/run_backtest.py` - Fuel子进程回测脚本（生成真实config.py到临时目录解决多进程问题）
- `domains/stock_hub/services/stock_backtest_service.py` - 回测执行服务（子进程+JSON通信）
- `domains/stock_hub/tools/backtest_tool.py` - 2个MCP工具（run/result）

### 修改文件
- `domains/stock_hub/api/mcp/server.py` - 注册回测工具

### 关键修复
- 多进程config问题：Windows spawn模式下子进程不继承sys.modules，改为生成真实config.py文件+PYTHONPATH注入

## Phase 3 - 因子分析服务

### 新增文件
- `domains/stock_hub/scripts/run_factor_analysis.py` - Fuel子进程分析脚本（调用tfunctions）
- `domains/stock_hub/services/stock_analysis_service.py` - 因子分析服务
- `domains/stock_hub/tools/analysis_tool.py` - 1个MCP工具（IC/分组分析）

### 修改文件
- `domains/stock_hub/api/mcp/server.py` - 注册分析工具

## Phase 4 - REST API

### 新增文件
- `domains/stock_hub/routes/__init__.py`
- `domains/stock_hub/routes/stock_routes.py` - 7个REST端点（因子CRUD + 回测 + 分析）

### 修改文件
无（路由注册待接入主路由器时添加一行）

### 待接入
- `app/routes/v1/router.py` 需添加: `api_router.include_router(stock_routes.router, prefix="/stock", tags=["stock"])`

## 迭代优化 - 代码审查修复

### 修改文件

**`services/stock_factor_service.py`**
- 修复BOM编码问题: `encoding="utf-8"` → `"utf-8-sig"` (9个H综合因子文件含UTF-8 BOM导致AST解析失败)

**`scripts/run_backtest.py`**
- 新增文件锁机制 (`_acquire_config_lock`/`_release_config_lock`): 防止并发回测互相覆盖config.py
- Windows使用`msvcrt.locking`, Linux使用`fcntl.flock`
- 删除未使用的`tempfile`导入和`tmp_dir = None`变量
- 更新模块文档字符串反映当前设计

**`services/stock_backtest_service.py`**
- 临时配置文件清理移至`finally`块，防止异常时泄漏
- 超时从硬编码`1800`改为`config.BACKTEST_TIMEOUT`（环境变量可配置）
- 清理`__import__("os")`模式，改为顶层`import os`

**`services/stock_analysis_service.py`**
- 超时从硬编码`600`改为`config.ANALYSIS_TIMEOUT`（环境变量可配置）
- 清理`__import__("os")`模式，改为顶层`import os`

**`config.py`**
- 新增`BACKTEST_TIMEOUT`和`ANALYSIS_TIMEOUT`配置项（支持环境变量覆盖）

**`routes/stock_routes.py`**
- 新增`POST /analysis/ic`端点（因子IC/ICIR/分组收益分析）
- 路由总数: 7 → 8

## Phase 5 - 前端UI集成

### 新增文件（前端 frontend/src/）

**Feature 模块 `features/stock-hub/`（5个文件）:**
- `types.ts` — 完整TypeScript类型定义（镜像后端Pydantic模型）
- `api.ts` — 8个REST端点的Axios封装（自定义unwrap处理非标准响应格式）
- `hooks.ts` — React Query hooks（因子列表/详情/分类/回测/分析）
- `store.ts` — Zustand UI状态（列配置/详情面板/回测tab）
- `index.ts` — 公共导出

**页面 `pages/stock-hub/`（3个文件）:**
- `FactorBrowser.tsx` — 因子浏览器（分类统计卡片+搜索+分类筛选+ResizableTable+分页+详情弹窗+代码查看）
- `BacktestPanel.tsx` — 回测面板（配置表单+因子列表编辑+回测历史+任务状态）
- `AnalysisView.tsx` — IC分析页（配置输入+IC/ICIR/T统计量指标卡片+分组收益ECharts柱状图）

### 修改文件（前端）
- `routes.tsx` — 新增 /stock-hub 路由组（3个子页面lazy加载）
- `components/layout/Sidebar.tsx` — 信息层追加"A股因子库"和"A股回测"导航项
- `lib/i18n/locales/zh-CN.json` — 追加 nav.stockHub/stockBacktest + stockHub.* 翻译
- `lib/i18n/locales/en-US.json` — 追加对应英文翻译

### 验证
- `npm run typecheck` 零错误通过
- 遵循现有架构模式（domain-driven, React Query, Zustand, i18n, shadcn/ui）
