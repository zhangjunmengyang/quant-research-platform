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
    # 判断币是否同时有现货和合约:检查两个字段是否都不为空
    df[factor_name] = np.where((df['symbol_spot'] != '') & (df['symbol_swap'] != ''), 1, 0)
    return df