def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    df['route_1'] = 2 * (df['high'] - df['low']) + (df['open'] - df['close'])
    df['route_2'] = 2 * (df['high'] - df['low']) + (df['close'] - df['open'])
    df.loc[df['route_1'] > df['route_2'], '盘中最短路径'] = df['route_2']
    df.loc[df['route_1'] <= df['route_2'], '盘中最短路径'] = df['route_1']
    df['最短路径_标准化'] = df['盘中最短路径'] / df['open']
    df['流动溢价'] = df['quote_volume'] / df['最短路径_标准化']

    df[factor_name] = df['流动溢价'].rolling(n, min_periods=2).std()

    del df['route_1']
    del df['route_2']
    del df['盘中最短路径']
    del df['最短路径_标准化']
    del df['流动溢价']

    return df