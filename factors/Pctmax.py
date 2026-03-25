# -*- coding: utf-8 -*-
"""
    公式：过滤24h内单k线超20%涨跌幅
"""
import numpy as np

def signal_multi_params(df, param_list) -> dict:
    ret = dict()
    for param in param_list:
        n = int(param)
        # 计算每根K线的涨跌幅
        df['pct_change'] = df['close'].pct_change(1)
        # 计算涨跌幅的绝对值
        df['abs_pct_change'] = df['pct_change'].abs()
        # 在n周期内，计算最大单K线涨跌幅的绝对值
        df['factor'] = df['abs_pct_change'].rolling(n, min_periods=1).max()
        ret[str(param)] = df['factor']
    return ret
