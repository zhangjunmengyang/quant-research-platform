def signal(*args):
    # MtmMean 指标
    df = args[0]
    n = args[1]
    factor_name = args[2]

    df['MtmMean'] = df['close'].pct_change(n).rolling(n).mean()
    df['std'] = df['close'].pct_change(n).rolling(n).std()
    df['MtmMean4'] = df['close'].pct_change(int(n/4)).rolling(int(n/4)).mean()
    df['std4'] = df['close'].pct_change(int(n/4)).rolling(int(n/4)).std()
    df[factor_name] = (df['MtmMean']) * (df['std'])  + (df['MtmMean4']) * (df['std4'])

    return df

def get_parameter():
    param_list = []
    n_list = [20, 50, 100, 500]
    for n in n_list:
        param_list.append([n])

    return param_list