"""
高级加密货币动量因子
目标：实现夏普比率2以上
author: AI量化研究员
"""
import pandas as pd
import numpy as np


def signal(*args):
    """
    高级动量因子计算
    结合多时间尺度动量、波动率调整、趋势强度和市场状态识别
    """
    df = args[0].copy()
    param = args[1]
    factor_name = args[2]

    # 兼容直接传入int和遍历传入list的情况
    if isinstance(param, list):
        n = param[0]
    else:
        n = param

    # 基础参数设置
    short_period = max(2, n // 4)  # 短期周期
    medium_period = max(3, n // 2)  # 中期周期
    long_period = n  # 长期周期

    # 1. 多时间尺度动量计算
    # 长期动量（主要趋势）
    long_pct_change = df['close'].pct_change(long_period)
    long_mtm_mean = long_pct_change.rolling(long_period).mean()
    long_mtm_std = long_pct_change.rolling(long_period).std()
    
    # 中期动量（中期趋势）
    medium_pct_change = df['close'].pct_change(medium_period)
    medium_mtm_mean = medium_pct_change.rolling(medium_period).mean()
    medium_mtm_std = medium_pct_change.rolling(medium_period).std()
    
    # 短期动量（短期趋势）
    short_pct_change = df['close'].pct_change(short_period)
    short_mtm_mean = short_pct_change.rolling(short_period).mean()
    short_mtm_std = short_pct_change.rolling(short_period).std()

    # 2. 波动率调整
    # 计算ATR-based波动率
    high_low = df['high'] - df['low']
    high_close_prev = np.abs(df['high'] - df['close'].shift(1))
    low_close_prev = np.abs(df['low'] - df['close'].shift(1))
    true_range = np.maximum(high_low, np.maximum(high_close_prev, low_close_prev))
    atr = true_range.rolling(window=n//2).mean()
    price_atr_ratio = atr / df['close']

    # 3. RSI作为趋势强度指标
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=n//3).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=n//3).mean()
    rs = gain / (loss + 1e-10)  # 防止除零
    rsi = 100 - (100 / (1 + rs))

    # 4. MACD作为趋势确认
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=9, adjust=False).mean()
    macd_histogram = macd - signal_line

    # 5. 布林带位置作为市场状态指标
    bb_middle = df['close'].rolling(window=n//2).mean()
    bb_std = df['close'].rolling(window=n//2).std()
    bb_upper = bb_middle + (bb_std * 2)
    bb_lower = bb_middle - (bb_std * 2)
    bb_position = (df['close'] - bb_lower) / (bb_upper - bb_lower + 1e-10)

    # 6. 综合因子计算
    # 长期趋势动量
    long_momentum = long_mtm_mean * long_mtm_std if long_mtm_std.iloc[-1] != 0 else 0
    # 中期趋势动量  
    medium_momentum = medium_mtm_mean * medium_mtm_std if medium_mtm_std.iloc[-1] != 0 else 0
    # 短期趋势动量
    short_momentum = short_mtm_mean * short_mtm_std if short_mtm_std.iloc[-1] != 0 else 0

    # 趋势强度调整（基于RSI偏离50的程度）
    trend_strength = (rsi - 50) / 50  # 归一化到[-1, 1]

    # 市场状态调整（基于布林带位置）
    market_state = np.where(bb_position > 0.8, -0.5,  # 超买区，降低做多信号
                           np.where(bb_position < 0.2, 0.5, 0))  # 超卖区，增强做多信号

    # 综合因子 = 长期趋势 + 中期趋势 + 短期趋势 + 趋势强度调整 + 市场状态调整 + MACD确认
    df[factor_name] = (
        long_momentum.fillna(0) * 0.4 +  # 长期趋势权重40%
        medium_momentum.fillna(0) * 0.3 +  # 中期趋势权重30%
        short_momentum.fillna(0) * 0.2 +  # 短期趋势权重20%
        trend_strength.fillna(0) * 0.05 +  # 趋势强度权重5%
        market_state * 0.05 +  # 市场状态权重5%
        np.tanh(macd_histogram.fillna(0)) * 0.1  # MACD确认权重10%，使用tanh限制范围
    )

    # 波动率调整（降低高波动期间的信号强度）
    vol_adjustment = 1 / (price_atr_ratio + 0.1)  # 防止过大调整
    df[factor_name] = df[factor_name] * vol_adjustment

    # 使用指数移动平均平滑因子
    df[factor_name] = df[factor_name].ewm(alpha=0.3, adjust=False).mean()

    # 处理异常值
    df[factor_name] = df[factor_name].replace([np.inf, -np.inf], np.nan)
    df[factor_name] = df[factor_name].fillna(0)

    return df


def get_parameter():
    """
    优化的参数设置，专注于高频有效的动量周期
    """
    param_list = []
    # 选择在加密货币市场中表现较好的周期
    n_list = [5, 8, 13, 21, 34]  # 斐波那契周期，适合加密货币波动特性
    for n in n_list:
        param_list.append([n])

    return param_list