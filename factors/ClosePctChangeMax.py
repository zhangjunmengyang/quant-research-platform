"""
2022  B圈新版课程 | 邢不行
author: 邢不行
微信: xbx6660
"""
"""
计算因子重要提醒：
1. 注意填充空值。因子数据不能为空，否则影响后面的选币计算。
2. 注意因子可能会无穷大或无穷小（在除数为0的情况下）。此时需要额外处理，否则影响后面的选币计算。
"""


def signal(*args):
    # ClosePctChangeMax
    df = args[0]
    n = args[1]
    factor_name = args[2]

    close_change = abs(df['close'].pct_change(1))
    df[factor_name] = close_change.rolling(n).max()

    return df


def get_parameter():
    param_list = []
    n_list = [24]
    for n in n_list:
        param_list.append(n)

    return param_list
