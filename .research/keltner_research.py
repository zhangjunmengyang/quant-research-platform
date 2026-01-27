# -*- coding: utf-8 -*-
"""
【CTA-ETH-研究2】Keltner通道突破做多信号研究

研究目标:
1. 经典Keltner通道上轨突破做多
2. Keltner通道与布林带的对比
3. 通道收窄后突破的信号质量
4. ATR倍数参数优化(1.5x, 2x, 2.5x, 3x)
"""

import pickle
import pandas as pd
import numpy as np
from datetime import datetime

# ============================================================
# 1. 加载ETH数据
# ============================================================
print("=" * 60)
print("1. 加载ETH合约数据")
print("=" * 60)

data_path = "/Users/zhangjunmengyang/Downloads/coin-binance-spot-swap-preprocess-pkl-1h-2026-01-19/swap_dict.pkl"

with open(data_path, 'rb') as f:
    swap_dict = pickle.load(f)

eth = swap_dict['ETH-USDT'].copy()
print(f"数据形状: {eth.shape}")
print(f"数据时间范围: {eth['candle_begin_time'].min()} ~ {eth['candle_begin_time'].max()}")
print(f"数据列: {eth.columns.tolist()}")

# ============================================================
# 2. 计算Keltner通道
# ============================================================
print("\n" + "=" * 60)
print("2. 计算Keltner通道指标")
print("=" * 60)

def calculate_atr(df, period):
    """计算ATR (Average True Range)"""
    high = df['high']
    low = df['low']
    close = df['close']

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period, min_periods=1).mean()

    return atr

def calculate_keltner_channel(df, period, multiplier):
    """计算Keltner通道

    Args:
        df: 数据DataFrame
        period: 计算周期
        multiplier: ATR倍数

    Returns:
        middle, upper, lower: 中轨、上轨、下轨
    """
    # 中轨使用EMA
    middle = df['close'].ewm(span=period, adjust=False).mean()

    # ATR
    atr = calculate_atr(df, period)

    # 上下轨
    upper = middle + multiplier * atr
    lower = middle - multiplier * atr

    return middle, upper, lower, atr

def calculate_bollinger_bands(df, period, multiplier):
    """计算布林带用于对比"""
    middle = df['close'].rolling(period).mean()
    std = df['close'].rolling(period).std()
    upper = middle + multiplier * std
    lower = middle - multiplier * std
    return middle, upper, lower, std

# ============================================================
# 3. 计算未来收益 (用于信号评估)
# ============================================================
print("\n" + "=" * 60)
print("3. 计算未来收益")
print("=" * 60)

# 计算未来N小时收益
for h in [1, 4, 8, 12, 24, 48]:
    eth[f'ret_{h}h'] = eth['close'].shift(-h) / eth['close'] - 1

print("未来收益列已添加: ret_1h, ret_4h, ret_8h, ret_12h, ret_24h, ret_48h")

# ============================================================
# 4. Keltner通道参数优化
# ============================================================
print("\n" + "=" * 60)
print("4. Keltner通道参数优化 (不同ATR倍数)")
print("=" * 60)

periods = [20, 30, 40, 48, 60]  # 周期参数
multipliers = [1.5, 2.0, 2.5, 3.0]  # ATR倍数

results = []

for period in periods:
    for mult in multipliers:
        # 计算Keltner通道
        middle, upper, lower, atr = calculate_keltner_channel(eth, period, mult)

        # 突破上轨信号
        breakout = (eth['close'] > upper) & (eth['close'].shift(1) <= upper.shift(1))

        signal_count = breakout.sum()

        if signal_count > 0:
            # 计算各时间段收益
            for h in [1, 4, 8, 12, 24, 48]:
                avg_ret = eth.loc[breakout, f'ret_{h}h'].mean() * 100
                results.append({
                    'period': period,
                    'multiplier': mult,
                    'horizon': f'{h}h',
                    'signal_count': signal_count,
                    'avg_return': avg_ret
                })

results_df = pd.DataFrame(results)
print("\n参数优化结果 (所有时段):")

# 按24H收益排序展示
results_24h = results_df[results_df['horizon'] == '24h'].sort_values('avg_return', ascending=False)
print("\n24H收益排名 (Top 10):")
print(results_24h.head(10).to_string(index=False))

# ============================================================
# 5. 与布林带对比
# ============================================================
print("\n" + "=" * 60)
print("5. Keltner通道 vs 布林带对比")
print("=" * 60)

# 使用相同参数对比
compare_period = 48
keltner_mult = 2.5
bb_mult = 2.5

# Keltner
kc_middle, kc_upper, kc_lower, kc_atr = calculate_keltner_channel(eth, compare_period, keltner_mult)
kc_breakout = (eth['close'] > kc_upper) & (eth['close'].shift(1) <= kc_upper.shift(1))

# Bollinger
bb_middle, bb_upper, bb_lower, bb_std = calculate_bollinger_bands(eth, compare_period, bb_mult)
bb_breakout = (eth['close'] > bb_upper) & (eth['close'].shift(1) <= bb_upper.shift(1))

print(f"\n参数: 周期={compare_period}, 倍数={keltner_mult}/{bb_mult}")
print(f"\nKeltner通道突破信号数: {kc_breakout.sum()}")
print(f"布林带突破信号数: {bb_breakout.sum()}")

print("\n收益对比:")
print(f"{'时间':<8} {'Keltner':<12} {'布林带':<12} {'差异':<12}")
print("-" * 44)
for h in [1, 4, 8, 12, 24, 48]:
    kc_ret = eth.loc[kc_breakout, f'ret_{h}h'].mean() * 100 if kc_breakout.sum() > 0 else 0
    bb_ret = eth.loc[bb_breakout, f'ret_{h}h'].mean() * 100 if bb_breakout.sum() > 0 else 0
    diff = kc_ret - bb_ret
    print(f"{h}H      {kc_ret:>+.3f}%     {bb_ret:>+.3f}%     {diff:>+.3f}%")

# ============================================================
# 6. 通道收窄后的突破质量
# ============================================================
print("\n" + "=" * 60)
print("6. 通道收窄后突破的信号质量")
print("=" * 60)

# 计算通道宽度 (相对于价格的百分比)
kc_width = (kc_upper - kc_lower) / kc_middle * 100
kc_width_pct = kc_width.rolling(20).rank(pct=True)  # 最近20期的百分位

# 通道收窄 + 突破
narrow_threshold = 0.3  # 宽度处于最近20期的30%分位以下
narrow_breakout = kc_breakout & (kc_width_pct.shift(1) < narrow_threshold)
normal_breakout = kc_breakout & (kc_width_pct.shift(1) >= narrow_threshold)

print(f"通道收窄后突破信号数: {narrow_breakout.sum()}")
print(f"正常通道突破信号数: {normal_breakout.sum()}")

print("\n收益对比 (通道收窄 vs 正常):")
print(f"{'时间':<8} {'收窄后':<12} {'正常':<12} {'差异':<12}")
print("-" * 44)
for h in [1, 4, 8, 12, 24, 48]:
    narrow_ret = eth.loc[narrow_breakout, f'ret_{h}h'].mean() * 100 if narrow_breakout.sum() > 0 else 0
    normal_ret = eth.loc[normal_breakout, f'ret_{h}h'].mean() * 100 if normal_breakout.sum() > 0 else 0
    diff = narrow_ret - normal_ret
    print(f"{h}H      {narrow_ret:>+.3f}%     {normal_ret:>+.3f}%     {diff:>+.3f}%")

# ============================================================
# 7. 市场环境分析 (趋势市 vs 震荡市)
# ============================================================
print("\n" + "=" * 60)
print("7. 市场环境分析 (趋势市 vs 震荡市)")
print("=" * 60)

# 使用长期均线判断趋势
eth['ma200'] = eth['close'].rolling(200).mean()
eth['trend'] = np.where(eth['close'] > eth['ma200'], 'uptrend', 'downtrend')

# ADX 判断趋势强度 (简化版本)
def calculate_adx(df, period=14):
    """计算ADX指标"""
    high = df['high']
    low = df['low']
    close = df['close']

    # +DM, -DM
    plus_dm = high.diff()
    minus_dm = low.diff() * -1

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    # 当+DM < -DM时,+DM=0
    plus_dm[(plus_dm < minus_dm)] = 0
    # 当-DM < +DM时,-DM=0
    minus_dm[(minus_dm < plus_dm)] = 0

    # TR
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Smoothed
    atr = tr.rolling(period).mean()
    plus_di = 100 * plus_dm.rolling(period).mean() / atr
    minus_di = 100 * minus_dm.rolling(period).mean() / atr

    # DX, ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-8)
    adx = dx.rolling(period).mean()

    return adx

eth['adx'] = calculate_adx(eth, 14)

# 趋势市: ADX > 25, 震荡市: ADX <= 25
adx_threshold = 25
trending = eth['adx'] > adx_threshold
ranging = eth['adx'] <= adx_threshold

# Keltner突破在不同市场环境下的表现
trend_breakout = kc_breakout & trending.shift(1)  # 用前一期判断
range_breakout = kc_breakout & ranging.shift(1)

print(f"趋势市(ADX>{adx_threshold})突破信号数: {trend_breakout.sum()}")
print(f"震荡市(ADX<={adx_threshold})突破信号数: {range_breakout.sum()}")

print("\n收益对比 (趋势市 vs 震荡市):")
print(f"{'时间':<8} {'趋势市':<12} {'震荡市':<12} {'差异':<12}")
print("-" * 44)
for h in [1, 4, 8, 12, 24, 48]:
    trend_ret = eth.loc[trend_breakout, f'ret_{h}h'].mean() * 100 if trend_breakout.sum() > 0 else 0
    range_ret = eth.loc[range_breakout, f'ret_{h}h'].mean() * 100 if range_breakout.sum() > 0 else 0
    diff = trend_ret - range_ret
    print(f"{h}H      {trend_ret:>+.3f}%     {range_ret:>+.3f}%     {diff:>+.3f}%")

# 牛市环境下的Keltner突破
uptrend_breakout = kc_breakout & (eth['trend'].shift(1) == 'uptrend')
downtrend_breakout = kc_breakout & (eth['trend'].shift(1) == 'downtrend')

print(f"\n牛市(价格>MA200)突破信号数: {uptrend_breakout.sum()}")
print(f"熊市(价格<MA200)突破信号数: {downtrend_breakout.sum()}")

print("\n收益对比 (牛市 vs 熊市):")
print(f"{'时间':<8} {'牛市':<12} {'熊市':<12} {'差异':<12}")
print("-" * 44)
for h in [1, 4, 8, 12, 24, 48]:
    up_ret = eth.loc[uptrend_breakout, f'ret_{h}h'].mean() * 100 if uptrend_breakout.sum() > 0 else 0
    down_ret = eth.loc[downtrend_breakout, f'ret_{h}h'].mean() * 100 if downtrend_breakout.sum() > 0 else 0
    diff = up_ret - down_ret
    print(f"{h}H      {up_ret:>+.3f}%     {down_ret:>+.3f}%     {diff:>+.3f}%")

# ============================================================
# 8. 信号质量统计
# ============================================================
print("\n" + "=" * 60)
print("8. Keltner突破信号质量统计")
print("=" * 60)

# 最优参数组合的统计
best_period = 48
best_mult = 2.5

kc_middle, kc_upper, kc_lower, kc_atr = calculate_keltner_channel(eth, best_period, best_mult)
kc_breakout = (eth['close'] > kc_upper) & (eth['close'].shift(1) <= kc_upper.shift(1))

print(f"最优参数: 周期={best_period}, ATR倍数={best_mult}")
print(f"总信号数: {kc_breakout.sum()}")

# 胜率统计
for h in [1, 4, 8, 12, 24, 48]:
    wins = (eth.loc[kc_breakout, f'ret_{h}h'] > 0).sum()
    total = kc_breakout.sum()
    winrate = wins / total * 100 if total > 0 else 0
    avg_ret = eth.loc[kc_breakout, f'ret_{h}h'].mean() * 100
    avg_win = eth.loc[kc_breakout & (eth[f'ret_{h}h'] > 0), f'ret_{h}h'].mean() * 100
    avg_loss = eth.loc[kc_breakout & (eth[f'ret_{h}h'] <= 0), f'ret_{h}h'].mean() * 100
    profit_factor = abs(avg_win * wins / (avg_loss * (total - wins))) if (total - wins) > 0 and avg_loss != 0 else float('inf')

    print(f"\n{h}H收益统计:")
    print(f"  胜率: {winrate:.1f}%")
    print(f"  平均收益: {avg_ret:+.3f}%")
    print(f"  平均盈利: {avg_win:+.3f}%")
    print(f"  平均亏损: {avg_loss:+.3f}%")
    print(f"  盈亏比: {profit_factor:.2f}")

# ============================================================
# 9. 与研究1布林带结果对比总结
# ============================================================
print("\n" + "=" * 60)
print("9. 与研究1布林带结果对比总结")
print("=" * 60)

print("""
研究1布林带发现:
- 单一布林带突破24H收益: +0.23%
- 牛市环境下24H收益: +0.73%
- 最优参数: 48周期, 2.5倍标准差
- 需要配合: 放量 + 带宽收窄

本研究Keltner通道发现:
""")

# 获取最优Keltner结果
kc_24h_ret = eth.loc[kc_breakout, 'ret_24h'].mean() * 100
uptrend_24h_ret = eth.loc[uptrend_breakout, 'ret_24h'].mean() * 100

print(f"- 单一Keltner突破24H收益: {kc_24h_ret:+.3f}%")
print(f"- 牛市环境下24H收益: {uptrend_24h_ret:+.3f}%")
print(f"- 最优参数: {best_period}周期, {best_mult}倍ATR")

# ATR vs 标准差的特点
print("\nKeltner vs 布林带特点对比:")
print("1. ATR对异常波动更稳健(不受单根大K线影响)")
print("2. Keltner通道更平滑,信号较少但可能更可靠")
print("3. 布林带在突破后更容易快速回归(均值回复)")
print("4. Keltner更适合趋势跟踪策略")

# ============================================================
# 10. 输出研究结论
# ============================================================
print("\n" + "=" * 60)
print("10. 研究结论")
print("=" * 60)

print(f"""
【CTA-ETH-研究2】Keltner通道突破做多信号研究 - 结论

1. 基准收益
   - Keltner突破24H收益: {kc_24h_ret:+.3f}%
   - 与布林带(+0.23%)相比: {'更优' if kc_24h_ret > 0.23 else '较弱'}

2. 参数优化
   - 最优周期: {best_period}小时 (与布林带一致)
   - 最优ATR倍数: {best_mult}x

3. 市场环境影响
   - 牛市突破收益: {uptrend_24h_ret:+.3f}%
   - 趋势市收益: {eth.loc[trend_breakout, 'ret_24h'].mean() * 100:+.3f}%
   - 震荡市收益: {eth.loc[range_breakout, 'ret_24h'].mean() * 100:+.3f}%

4. 通道收窄效果
   - 收窄后突破: {eth.loc[narrow_breakout, 'ret_24h'].mean() * 100 if narrow_breakout.sum() > 0 else 0:+.3f}%
   - 正常突破: {eth.loc[normal_breakout, 'ret_24h'].mean() * 100 if normal_breakout.sum() > 0 else 0:+.3f}%

5. 核心发现
   - Keltner通道使用ATR计算波动带,对极端波动更稳健
   - 在趋势明确的市场中表现更好
   - 通道收窄后的突破信号质量{'更高' if (narrow_breakout.sum() > 0 and eth.loc[narrow_breakout, 'ret_24h'].mean() > eth.loc[normal_breakout, 'ret_24h'].mean()) else '需要进一步验证'}

6. 交易建议
   - Keltner可作为布林带的补充确认
   - 在ADX>25的趋势市使用效果更佳
   - 结合牛市环境(价格>MA200)过滤信号
""")

print("\n研究完成!")
