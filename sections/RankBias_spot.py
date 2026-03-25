"""
邢不行｜策略分享会
选币策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
import numpy as np
import pandas as pd


def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    con = df['is_spot'] == 1

    # 仅对 is_spot == 1 的行进行 rank 计算
    df.loc[con, 'rank'] = df.loc[con].groupby('candle_begin_time')[f'QuoteVolumeMean_{n}'].rank(ascending=True, method='min')

    # 仅对 is_spot == 1 的行进行 rank_mean 计算
    df.loc[con, 'rank_mean'] = df.loc[con].groupby('symbol')['rank'].transform(lambda x: x.rolling(n, min_periods=1).mean())

    # 仅对 is_spot == 1 的行进行 rank_bias 计算
    df.loc[con, 'rank_bias'] = df.loc[con]['rank'] / df.loc[con]['rank_mean']

    # 将最终结果赋值给 factor_name 列
    df[factor_name] = df['rank_bias']

    return df


def get_factor_list(n):
    return [
        ('QuoteVolumeMean', n)
    ]

