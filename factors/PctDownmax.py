# -*- coding: utf-8 -*-
"""
    公式：
"""


def signal_multi_params(df, param_list) -> dict:
    ret = dict()
    for param in param_list:
        n = int(param)
        df['该小时涨跌幅'] = df['close'].pct_change(1)
        df['factor'] = df['该小时涨跌幅'].rolling(n).min()
        ret[str(param)] = df['factor']
    return ret
