def signal(*args):
    # MtmMeanStdV1
    df = args[0]
    n = args[1]
    factor_name = args[2]

    MtmMean = df['close'].pct_change(n).rolling(n).mean()
    std = df['close'].pct_change(n).rolling(n).std()
    df[factor_name] = MtmMean * std

    return df