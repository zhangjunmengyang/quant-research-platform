"""
加密货币动量因子
基于价格变化率的动量指标，用于识别加密货币的趋势方向
"""
import pandas as pd
import numpy as np


def signal(*args):
    """
    计算加密货币动量因子
    参数:
    - df: 包含价格数据的DataFrame，必须包含'close'列
    - param: 参数列表，param[0]为动量周期
    - factor_name: 因子名称
    """
    df = args[0]
    param = args[1]
    factor_name = args[2]

    # 处理参数
    if isinstance(param, list):
        n = param[0]  # 动量计算周期
        threshold = param[1] if len(param) > 1 else 0  # 可选的阈值参数
    else:
        n = param
        threshold = 0

    # 计算n周期的价格变化率
    pct_change_n = df['close'].pct_change(periods=n)
    
    # 计算n周期内价格变化率的移动平均
    mtm_mean = pct_change_n.rolling(window=n).mean()
    
    # 计算n周期内价格变化率的标准差
    mtm_std = pct_change_n.rolling(window=n).std()
    
    # 计算动量因子值 - 结合均值和标准差
    df[factor_name] = mtm_mean * mtm_std
    
    # 可选：根据阈值过滤信号
    if threshold > 0:
        df[factor_name] = df[factor_name].where(
            df[factor_name].abs() > threshold, 0
        )

    # 处理NaN值
    df[factor_name] = df[factor_name].fillna(0)
    
    return df


def get_parameter():
    """
    返回参数组合列表
    """
    param_list = []
    # 测试不同的动量周期
    n_list = [3, 5, 8, 13, 21, 34, 55]  # 斐波那契数列，适合加密货币波动
    for n in n_list:
        param_list.append([n])  # 可以添加阈值参数 [n, threshold]

    return param_list