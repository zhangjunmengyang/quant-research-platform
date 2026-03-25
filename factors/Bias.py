"""
邢不行™️ 策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx6660

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""


def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    df['bias'] = df['close'] / df['close'].rolling(n, min_periods=1).mean()

    df[factor_name] = df['bias']

    return df


def signal_multi_params(df, param_list) -> dict:
    ret = dict()
    for param in param_list:
        n = int(param)
        ret[str(param)] = df['close'] / df['close'].rolling(n, min_periods=1).mean()
    return ret
