"""
Stock Hub - A股千因子选股研究

提供A股因子查询、回测执行、因子分析和报告生成功能。
通过子进程隔离调用选股框架(Fuel Python环境)。

主要组件:
- StockFactorService: 因子元数据查询
- StockBacktestService: 回测执行(待实现)
- StockAnalysisService: 因子分析(待实现)
- MCP Server: Model Context Protocol 服务
"""

__version__ = "1.0.0"
