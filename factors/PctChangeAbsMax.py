def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    df['pct'] = df['close'].pct_change().abs()
    df[factor_name] = df['pct'].rolling(n, min_periods=1).max()

    return df