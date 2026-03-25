def signal(candle_df, param, *args):
    """
    计算 BIAS 因子，并生成数值在 [0, -0.15] 区间内的信号
    :param candle_df: 单个币种的K线数据
    :param param: 元组参数，包含 (计算周期)，例如 (6) 表示6日BIAS
    :param args: 其他参数，依次为：
        - args[0]: 因子名称前缀（例如 "BIAS"）
        - args[1]: 价格列名（默认 "close"）
    :return: 包含 BIAS 因子和信号的K线数据，新增两列：
        - BIAS 值（例如 BIAS_6）
        - 信号（例如 BIAS_signal）
    """
    # 解析参数
    n = param[0]  # 从 param 中获取计算周期（如6日）
    therold = param[1]#设置门槛值
    factor_name = args[0]  # 从额外参数中获取因子名称

    # 检查输入有效性
    if 'close' not in candle_df.columns:
        raise ValueError(f"价格列close不存在于 DataFrame 中")
    if n <= 0:
        raise ValueError("计算周期必须为正整数")

    # 计算 BIAS 指标 ------------------------------------------------
    # 计算 N 日移动平均
    ma = candle_df['close'].rolling(window=n, min_periods=1).mean()
    # BIAS = (价格 - MA) / MA
    bias = (candle_df['close'] - ma) / ma
    candle_df[f"Bias_{n}"] = bias  # 例如列名 "BIAS_6"

    # 生成信号：BIAS 在 [0, -0.15] 区间内 ----------------------------
    # 条件：-0.15 <= BIAS <= 0
    signal_condition = (bias >= therold) & (bias <= 0)
    candle_df[factor_name] = signal_condition

    return candle_df
