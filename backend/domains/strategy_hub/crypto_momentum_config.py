"""
加密货币动量策略配置
"""
from domains.engine.core.model.strategy_config import StrategyConfig
from domains.engine.core.model.backtest_config import BacktestConfig


def create_crypto_momentum_strategy():
    """
    创建加密货币动量策略配置
    """
    # 定义策略参数
    strategy_conf = StrategyConfig(
        name='Crypto Momentum Strategy',
        factors=[
            {
                'factor_name': 'CryptoMomentum',
                'factor_params': [5],  # 使用5周期动量
                'factor_file': 'CryptoMomentum.py',
                'direction': 1,  # 正向：价格上涨时买入
                'weight': 1.0
            }
        ],
        entry_rule={
            'condition': 'factor_value > 0.001',  # 动量因子大于阈值时进入
            'percent': 0.8  # 使用80%资金
        },
        exit_rule={
            'condition': 'factor_value < -0.001',  # 动量反转时退出
            'percent': 1.0
        },
        position sizing={
            'method': 'equal_weight',  # 等权重分配
            'max_positions': 10  # 最大持仓数量
        },
        risk_management={
            'max_drawdown': 0.15,  # 最大回撤15%
            'max_position_size': 0.1,  # 单笔最大仓位10%
            'stop_loss': 0.05  # 止损5%
        }
    )
    
    return strategy_conf


def create_backtest_config():
    """
    创建回测配置
    """
    backtest_conf = BacktestConfig(
        start_date='2023-01-01',
        end_date='2024-01-01',
        initial_capital=100000,  # 初始资金10万
        data_frequency='1d',  # 日线数据
        symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT'],  # 主流币种
        strategies=[create_crypto_momentum_strategy()],
        rebalance_freq='weekly',  # 每周调仓
        transaction_cost=0.001  # 交易成本0.1%
    )
    
    return backtest_conf