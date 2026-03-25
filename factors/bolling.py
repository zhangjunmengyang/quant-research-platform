
def signal(*args):
    # Bolling 指标
    df = args[0]
    n = args[1]
    factor_name = args[2]

    # 计算布林上下轨
    df['std'] = df['close'].rolling(n, min_periods=1).std()
    df['ma'] = df['close'].rolling(n, min_periods=1).mean()
    df['upper'] = df['ma'] + 2.0 * df['std']
    df['lower'] = df['ma'] - 2.0 * df['std']

    df['bolling_type'] = 0
    condition_1 = df['close'] < df['lower']
    condition_2 = (df['close'] > df['lower']) & (df['close'] <= df['ma'])
    condition_3 = (df['close'] > df['ma']) & (df['close'] < df['upper'])
    condition_4 = (df['close'] > df['upper'])
    df.loc[condition_1, 'bolling_type'] = 1
    df.loc[condition_2, 'bolling_type'] = 2
    df.loc[condition_3, 'bolling_type'] = 3
    df.loc[condition_4, 'bolling_type'] = 4
    df[factor_name] = df['bolling_type']

    # 删除多余列
    del df['std'], df['ma'], df['upper'], df['lower']

    return df
