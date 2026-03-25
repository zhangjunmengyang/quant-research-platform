"""
高级加密货币动量策略配置
author: AI量化研究员
"""
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 因子配置
FACTOR_CONFIG = {
    'factor_name': 'AdvancedCryptoMomentum',  # 使用新创建的高级动量因子
    'params': [5, 8, 13, 21, 34],  # 使用优化的参数
    'top_n': 10,  # 选取前10个最强信号的币种
    'rebalance_freq': 'daily',  # 日度再平衡
}

# 回测配置
BACKTEST_CONFIG = {
    'start_date': '2023-01-01',
    'end_date': '2024-12-31',
    'initial_capital': 100000,  # 初始资金10万
    'transaction_cost': 0.001,  # 0.1%交易成本
    'slippage': 0.0005,  # 0.05%滑点
    'min_position_size': 0.01,  # 最小仓位1%
    'max_position_size': 0.1,   # 最大仓位10%
}

# 风险管理配置
RISK_MANAGEMENT = {
    'max_drawdown_limit': 0.2,  # 最大回撤限制20%
    'max_leverage': 1.0,  # 最大杠杆1倍
    'stop_loss_pct': 0.08,  # 8%止损
    'take_profit_pct': 0.15,  # 15%止盈
    'volatility_target': 0.2,  # 目标年化波动率20%
}

# 评估指标
EVALUATION_METRICS = [
    'sharpe_ratio',
    'max_drawdown',
    'total_return',
    'annual_return',
    'volatility',
    'alpha',
    'beta',
    'information_ratio',
    'calmar_ratio'
]