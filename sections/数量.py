"""
邢不行™️ 策略分享会
选币策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import pandas as pd

def signal(*args):
    """
    计算每个币在每个时间点是否为“新币”。
    这是一个截面因子，它会为每个币在每个时间点生成一个值。
    如果币的上市时间小于 n 小时，则为 1 (是新币)，否则为 0。
    """
    df = args[0]
    n = args[1]  # n: 定义新币的小时数阈值
    factor_name = args[2]

    # 确保 'candle_begin_time' 是 datetime 类型
    df['candle_begin_time'] = pd.to_datetime(df['candle_begin_time'])

    # 计算每个币种的上市时间（在数据集中首次出现的时间）
    # 使用 transform 将每个币种的最小时间广播到其所有行
    df['listing_time'] = df.groupby('symbol')['candle_begin_time'].transform('min')

    # 计算每个币种在每个时间点的存在时长（小时）
    time_deltas = df['candle_begin_time'] - df['listing_time']
    total_hours = time_deltas.dt.total_seconds() / 3600

    # 判断是否为新币，并生成 0/1 因子值
    df[factor_name] = (total_hours < n).astype(int)
    
    # 移除中间列
    df.drop(columns=['listing_time'], inplace=True, errors='ignore')

    return df


def get_factor_list(n):
    """
    此截面因子不依赖于任何其他预先计算的因子。
    它直接使用 'candle_begin_time' 和 'symbol' 列进行计算。
    因此，返回一个空列表。
    """
    return []
