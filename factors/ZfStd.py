"""
邢不行™️ 策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx6660

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import numpy as np


def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    df['mtm'] = df['close'].pct_change()
    df['zf'] = (df['high'] - df['low']) / df['open']
    df['zf'] = np.where(df['mtm'] > 0, df['zf'], -df['zf'])
    df['std'] = df['zf'].rolling(n, min_periods=1).std()

    df[factor_name] = df['std']

    return df
