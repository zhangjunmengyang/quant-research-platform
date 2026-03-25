import pandas as pd
import numpy as np


def signal(*args):
    """
    计算Max_ZfMeanQ_VolMeanQ因子

    参数:
        *args: 包含以下参数的可变参数列表
            df: DataFrame, 包含价格和成交量数据
            n: int, 计算窗口大小
            factor_name: str, 因子名称

    返回:
        df: DataFrame, 添加了因子列的数据框

    说明:
        1. 计算价格振幅 (最高价-最低价)/开盘价
        2. 计算振幅的滚动均值
        3. 计算振幅均值的滚动排名百分比 (Q1)
        4. 计算成交量的滚动均值
        5. 计算成交量均值的滚动排名百分比 (Q2)
        6. 取Q1和Q2的最大值作为最终因子值
    """
    df = args[0]
    n = args[1]
    factor_name = args[2]

    df['振幅'] = (df['high'] - df['low']) / df['open']
    df['振幅均值'] = df['振幅'].rolling(n, min_periods=1).mean()
    df['Q1'] = df['振幅均值'].rolling(n, min_periods=1).rank(ascending=True, pct=True)

    df['VolMean'] = df['volume'].rolling(n, min_periods=1).mean()
    df['Q2'] = df['VolMean'].rolling(n, min_periods=1).rank(ascending=True, pct=True)

    df[factor_name] = df[['Q1', 'Q2']].max(axis=1)
    return df
