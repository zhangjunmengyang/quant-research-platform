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
    # MtmMeanStd
    df = args[0]
    param = args[1]
    factor_name = args[2]

    # 兼容直接传入int和遍历传入list的情况
    if isinstance(param, list):
        n = param[0]
    else:
        n = param

    mtmmean = df['close'].pct_change(n).rolling(n).mean()
    mtmstd = df['close'].pct_change(n).rolling(n).std()
    df[factor_name] = (mtmmean * mtmstd)

    return df


def get_parameter():
    param_list = []
    n_list = [3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
    for n in n_list:
        param_list.append([n])

    return param_list