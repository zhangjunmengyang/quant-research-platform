import numpy as np


def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    df['均价'] = (df['close'] + df['high'] + df['low']) / 3
    df['涨跌幅'] = df['均价'].pct_change()
    df['振幅'] = (df['high'] - df['low']) / df['open']

    df['下跌振幅'] = np.where(df['涨跌幅'] < 0, df['振幅'], 0)
    df['振幅均值'] = df['下跌振幅'].rolling(n, min_periods=1).mean()
    df['下跌rank'] = df['振幅均值'].rolling(n, min_periods=1).rank(ascending=True, pct=True)

    df['上涨振幅'] = np.where(df['涨跌幅'] > 0, df['振幅'], 0)
    df['振幅均值'] = df['上涨振幅'].rolling(n, min_periods=1).mean()
    df['上涨rank'] = df['振幅均值'].rolling(n, min_periods=1).rank(ascending=True, pct=True)

    df[factor_name] = df['上涨rank'] + df['下跌rank']
    return df