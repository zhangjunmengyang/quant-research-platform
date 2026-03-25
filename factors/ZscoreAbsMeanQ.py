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

    df['Zscore'] = (df['close'] - df['close'].rolling(n, min_periods=1).mean()) / df['close'].rolling(n, min_periods=1).std()
    df['ZscoreAbsMean'] = df['Zscore'].abs().rolling(n, min_periods=1).mean()

    df[factor_name] = df['ZscoreAbsMean'].rolling(n, min_periods=1).rank(ascending=True, pct=True)

    return df
