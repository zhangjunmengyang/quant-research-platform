"""
邢不行™️ 策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx6660

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""


def signal(*args):
    """
    计算n周期内的最大单周期价格上涨率。
    例如，n=24，数据周期为1H，则计算过去24小时内，任意1小时的最大涨幅。
    """
    df = args[0]
    n = args[1]
    factor_name = args[2]

    # 计算每个周期的价格变化率
    pct_change = df['close'].pct_change()

    # 计算过去n个周期内，价格变化率的最大值
    df[factor_name] = pct_change.rolling(n, min_periods=1).max()

    return df
