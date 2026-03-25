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

    df['均价'] = (df['close'] + df['high'] + df['low']) / 3

    df['涨跌幅'] = df['均价'].pct_change()
    df['振幅'] = (df['high'] - df['low']) / df['open']
    df['振幅'] = np.where(df['涨跌幅'] > 0, df['振幅'], 0)
    df['振幅均值'] = df['振幅'].rolling(n, min_periods=1).mean()

    df[factor_name] = df['振幅均值'].rolling(n, min_periods=1).rank(ascending=True, pct=True)

    return df
