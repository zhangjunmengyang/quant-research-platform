"""
邢不行｜策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import numpy as np


def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    # 确保 symbol 列是字符串并去除空格
    is_btc = df['symbol'].astype(str).str.strip() == 'BTC-USDT'
    
    # BTC-USDT 赋值为 0 (配合 Ascending=True，越小排名越靠前)
    # 其他币种赋值为 NaN (不参与排名)
    df[factor_name] = np.where(is_btc, 0, np.nan)

    return df
