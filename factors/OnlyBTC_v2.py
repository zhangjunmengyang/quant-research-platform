import numpy as np
import pandas as pd


def signal(*args):
    df = args[0]
    n = args[1]
    factor_name = args[2]

    is_btc = (df['symbol'] == 'BTC-USDT') | (df['symbol'] == 'BTCUSDT')
    df[factor_name] = np.where(is_btc, 1, np.nan)

    return df


def signal_multi_params(df, param_list) -> dict:
    is_btc = (df['symbol'] == 'BTC-USDT') | (df['symbol'] == 'BTCUSDT')
    series = pd.Series(np.where(is_btc, 1, np.nan), index=df.index)
    return {str(param): series for param in param_list}