"""
选币策略 | 邢不行
author: 邢不行
微信: xbx6660
"""


#  "因子名": "Volatility",
#  "分类": "波动率因子",
#  "数据字段": "close"
#  "算符": "rolling, std",
#  "简单介绍": "这个因子计算了币种的波动率。"


def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    change = df['close'].pct_change()
    df[factor_name] = change.rolling(n).std()

    return df


def get_parameter():
    param_list = []
    n_list = [3, 7, 14, 30, 72, 168, 336, 720]
    for n in n_list:
        param_list.append(n)

    return param_list
