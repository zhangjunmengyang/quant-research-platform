"""
邢不行™️ 策略分享会
仓位管理框架

版权所有 ©️ 邢不行
微信: xbx6660

本代码仅供个人学习使用，未经授权不得复制、修改或用于商业用途。

Author: 邢不行
"""
extra_data_dict = {
    'coin-cap': ['circulating_supply']
}

def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    # 计算市值因子（越小越好）
    df['circulating_mcap'] = df['circulating_supply'] * df['close'].rolling(n).mean()

    df['mtmmean'] = (df['close'] / df['close'].shift(n)).rolling(n).mean()

    # 计算成交额因子（越小越好，选择低成交额）
    df['quote_volume_mean'] = df['quote_volume'].rolling(n).mean()

    # 综合因子：市值小 * 成交额低
    df[factor_name] = df['circulating_mcap'] * df['quote_volume_mean'] * df['mtmmean']
    return df
