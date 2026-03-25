"""
邢不行™️ 策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx6660

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import pandas as pd
import numpy as np

def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    # 转换时间为 pandas Series
    candle_series = pd.to_datetime(pd.Series(df['candle_begin_time']))

    # 满足有合约有现货的条件
    cond = (df['symbol_swap'] != '') & (df['symbol_spot'] != '')

    # 找到首次满足条件的索引
    if cond.any():
        first_idx = cond[cond].index[0]
        first_time = candle_series.iloc[first_idx]

        # 计算每一行到首次满足条件的时间差（小时）
        hours_since_first = (candle_series - first_time).dt.total_seconds() / 3600

        # 只有满足条件的行才赋值，其它为 0
        df[factor_name] = np.where(cond, hours_since_first, np.nan)
    else:
        df[factor_name] = np.nan

    return df
