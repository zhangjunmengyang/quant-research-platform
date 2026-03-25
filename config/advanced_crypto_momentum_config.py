"""
框架标准配置文件
用于运行高级加密货币动量策略
"""
from datetime import datetime

# 回测配置
backtest_name = "Advanced_Crypto_Momentum_Strategy"
start_date = '2023-01-01'
end_date = '2024-12-31'

# 账户配置
account_type = '普通账户'
leverage = 1.0  # 杠杆
initial_usdt = 100000  # 初始资金10万
margin_rate = 0.05  # 维持保证金率5%

# 交易费用
swap_c_rate = 6e-4  # 合约手续费 0.06%
spot_c_rate = 2e-3  # 现货手续费 0.2%

# 最小订单限制
spot_min_order_limit = 10  # 现货最小下单量
swap_min_order_limit = 5   # 合约最小下单量

# 策略配置
black_list = []  # 黑名单
white_list = []  # 白名单
min_kline_num = 168  # 最少上市时间（小时）

# 策略列表 - 使用我们开发的高级动量因子
strategy_list = [
    {
        'strategy': 'mix_28_win',  # 混合策略
        'select_scope': 'swap',  # 选择永续合约
        'hold_period': '1H',  # 持仓周期
        'cap_weight': 1.0,  # 资金权重
        'order_first': False,
        'period_num': 28,  # 周期数
        
        # 动量因子配置
        'factor_list': [
            {
                'name': 'AdvancedCryptoMomentum',  # 使用我们开发的高级动量因子
                'param': 5,  # 参数
                'weight': 1.0,
                'is_reverse': False,  # 不反转（正值看涨）
            }
        ],
        
        # 选股配置
        'long_select_coin_num': 10,  # 做多币种数量
        'short_select_coin_num': 0,  # 做空币种数量
        'long_cap_weight': 1.0,  # 做多资金权重
        'short_cap_weight': 0.0,  # 做空资金权重
        
        # 偏移配置（用于多时间框架分析）
        'offset_list': [0]
    }
]

# 重新平衡模式
rebalance_mode = None

# 平均价格列
avg_price_col = 'avg_price_1m'