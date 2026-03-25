"""
邢不行｜策略分享会
选币策略框架𝓟𝓻𝓸

版权所有 ©️ 邢不行
微信: xbx1717

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""


def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    df['rank'] = df.groupby('candle_begin_time')[f'QuoteVolumeMean_{n}'].rank(ascending=True, method='min')
    df['rank_mean'] = df.groupby('symbol')['rank'].transform(lambda x: x.rolling(n, min_periods=1).mean())
    df['rank_bias'] = df['rank'] / df['rank_mean']

    df[factor_name] = df['rank_bias']

    return df


def get_factor_list(n):
    return [
        ('QuoteVolumeMean', n)
    ]
