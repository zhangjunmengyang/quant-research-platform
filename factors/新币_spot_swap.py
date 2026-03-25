
def signal(*args):
    df = args[0]
    n = args[1]  
    factor_name = args[2]

    # 获取币种的合约和现货都上了之后的首次出现时间，
    mask = (
            df['symbol_spot'].notna() & (df['symbol_spot'] != '') &
            df['symbol_swap'].notna() & (df['symbol_swap'] != '')
    )
    first_appear = df.loc[mask, 'candle_begin_time'].min()

    # 计算当前时间与首次出现时间的小时差
    df[factor_name] = (df['candle_begin_time'] - first_appear).dt.total_seconds() / 3600

    return df