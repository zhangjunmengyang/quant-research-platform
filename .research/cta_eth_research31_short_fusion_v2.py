"""
CTA-ETH-研究31: 做空信号投票融合研究 v2

重新设计信号逻辑，基于原研究发现:
- 研究25: 强熊市+假突破+24H涨>10%+强量缩 (72H胜率100%, 7信号)
- 研究27: 熊市天量下跌 (72H胜率82.6%, 23信号)
- 研究29: 熊市反弹衰竭 (12H胜率87.5%, 16信号)
- 研究30: 日周共振+反弹+RSI (24H胜率83.3%, 12信号)

关键修改:
1. 调整信号阈值使信号数量接近原研究
2. 验证做空收益的计算方式
3. 探索信号间的时间窗口重叠
"""

import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ========================================
# 1. 加载数据
# ========================================

data_path = "/Users/zhangjunmengyang/Downloads/coin-binance-spot-swap-preprocess-pkl-1h-2026-01-19/swap_dict.pkl"

with open(data_path, 'rb') as f:
    swap_dict = pickle.load(f)

eth = swap_dict['ETH-USDT'].copy()

# 设置时间索引
eth['candle_begin_time'] = pd.to_datetime(eth['candle_begin_time'])
eth = eth.set_index('candle_begin_time')

# 过滤有效数据
eth = eth[eth['close'].notna()].copy()

print(f"ETH数据: {eth.index[0]} ~ {eth.index[-1]}, 共{len(eth)}行")

# ========================================
# 2. 基础指标计算
# ========================================

# 均线
eth['MA50'] = eth['close'].rolling(50).mean()
eth['MA120'] = eth['close'].rolling(120).mean()
eth['MA200'] = eth['close'].rolling(200).mean()

# 日线均线 (用24H近似)
eth['MA20_daily'] = eth['close'].rolling(20*24).mean()
eth['MA50_daily'] = eth['close'].rolling(50*24).mean()

# 周线均线
eth['MA5_weekly'] = eth['close'].rolling(5*24*7).mean()
eth['MA10_weekly'] = eth['close'].rolling(10*24*7).mean()

# 成交量均线
eth['vol_ma10'] = eth['volume'].rolling(10).mean()
eth['vol_ma20'] = eth['volume'].rolling(20).mean()
eth['vol_ma24'] = eth['volume'].rolling(24).mean()

# RSI(14)
delta = eth['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / avg_loss
eth['RSI'] = 100 - (100 / (1 + rs))

# 区间涨幅
eth['ret_1h'] = eth['close'].pct_change(1) * 100
eth['ret_8h'] = eth['close'].pct_change(8) * 100
eth['ret_10h'] = eth['close'].pct_change(10) * 100
eth['ret_12h'] = eth['close'].pct_change(12) * 100
eth['ret_24h'] = eth['close'].pct_change(24) * 100
eth['ret_48h'] = eth['close'].pct_change(48) * 100

# 未来价格变化 (价格下跌时为正值，即做空收益)
eth['fwd_ret_12h'] = -eth['close'].pct_change(-12) * 100
eth['fwd_ret_24h'] = -eth['close'].pct_change(-24) * 100
eth['fwd_ret_48h'] = -eth['close'].pct_change(-48) * 100
eth['fwd_ret_72h'] = -eth['close'].pct_change(-72) * 100

# 区间最高/最低
eth['high_8h'] = eth['high'].rolling(8).max()
eth['high_12h'] = eth['high'].rolling(12).max()
eth['high_24h'] = eth['high'].rolling(24).max()
eth['low_24h'] = eth['low'].rolling(24).min()

# ========================================
# 3. 定义做空信号
# ========================================

def signal_25_v2(df):
    """
    研究25: 强熊市+假突破+24H涨>10%+强量缩
    目标: 约7个信号

    逻辑: 熊市中快速反弹但量能不足，假突破后做空
    """
    # 强熊市: MA50显著低于MA120
    strong_bear = df['MA50'] < df['MA120'] * 0.95

    # 24H涨幅显著 (>10%)
    rally_24h = df['ret_24h'] > 10

    # 量缩: 当前成交量低于均量
    vol_shrink = df['volume'] < 0.8 * df['vol_ma10']

    # 假突破: 当日最高曾突破某阻力位但收盘回落
    # 改为: 价格曾接近但未能站稳上方均线
    fake_breakout = (df['high_8h'] > df['MA50']) & (df['close'] < df['MA50'])

    signal = strong_bear & rally_24h & vol_shrink & fake_breakout
    return signal


def signal_27_v2(df):
    """
    研究27: 熊市天量下跌
    目标: 约23个信号

    逻辑: 熊市中恐慌性抛售后，短期可能有反弹，但中期继续下跌
    原研究72H胜率82.6%，说明做空后72H价格继续下跌
    """
    # 熊市
    bear_market = df['MA50'] < df['MA200']

    # 放量 (>3倍均量，放宽条件)
    high_volume = df['volume'] > 3 * df['vol_ma20']

    # 当前1H跌幅较大
    drop_1h = df['ret_1h'] < -2

    # 24H累计已经下跌
    cum_drop_24h = df['ret_24h'] < -3

    signal = bear_market & high_volume & drop_1h & cum_drop_24h
    return signal


def signal_29_v2(df):
    """
    研究29: 熊市反弹衰竭
    目标: 约16个信号

    逻辑: 熊市中反弹后出现回落，显示反弹力量衰竭
    原研究12H胜率87.5%
    """
    # 熊市
    bear_market = df['MA50'] < df['MA200']

    # 近期有较大反弹
    recent_rally = df['ret_12h'] > 8

    # 从高点回落
    rolling_high = df['high'].rolling(12).max()
    pullback = (rolling_high - df['close']) / rolling_high * 100
    has_pullback = pullback > 2

    signal = bear_market & recent_rally & has_pullback
    return signal


def signal_30_v2(df):
    """
    研究30: 日周共振+反弹+RSI
    目标: 约12个信号

    逻辑: 多周期空头排列+反弹超买，做空时机
    原研究24H胜率83.3%
    """
    # 日线空头排列
    daily_bear = df['MA20_daily'] < df['MA50_daily']

    # 周线空头排列
    weekly_bear = df['MA5_weekly'] < df['MA10_weekly']

    # 反弹
    rally = df['ret_24h'] > 8

    # RSI超买
    rsi_overbought = df['RSI'] > 70

    signal = daily_bear & weekly_bear & rally & rsi_overbought
    return signal


# ========================================
# 4. 信号去重函数
# ========================================

def remove_overlap_signals(signal_series, min_gap_hours=24):
    """去除重叠信号，保留首次触发"""
    signal_idx = signal_series[signal_series].index.tolist()
    if not signal_idx:
        return signal_series

    filtered = [signal_idx[0]]
    for idx in signal_idx[1:]:
        hours_diff = (idx - filtered[-1]).total_seconds() / 3600
        if hours_diff >= min_gap_hours:
            filtered.append(idx)

    result = pd.Series(False, index=signal_series.index)
    result.loc[filtered] = True
    return result


# ========================================
# 5. 计算信号
# ========================================

print("\n" + "="*60)
print("初始信号统计:")
print("="*60)

# 计算原始信号
eth['sig_25_raw'] = signal_25_v2(eth)
eth['sig_27_raw'] = signal_27_v2(eth)
eth['sig_29_raw'] = signal_29_v2(eth)
eth['sig_30_raw'] = signal_30_v2(eth)

for sig_name in ['sig_25_raw', 'sig_27_raw', 'sig_29_raw', 'sig_30_raw']:
    count = eth[sig_name].sum()
    print(f"{sig_name}: {count}个信号")

# 去重
eth['sig_25'] = remove_overlap_signals(eth['sig_25_raw'], 72)  # 72H间隔
eth['sig_27'] = remove_overlap_signals(eth['sig_27_raw'], 72)
eth['sig_29'] = remove_overlap_signals(eth['sig_29_raw'], 12)  # 12H间隔
eth['sig_30'] = remove_overlap_signals(eth['sig_30_raw'], 24)

print("\n去重后信号统计:")
for sig_name in ['sig_25', 'sig_27', 'sig_29', 'sig_30']:
    count = eth[sig_name].sum()
    print(f"{sig_name}: {count}个信号")


# ========================================
# 6. 分析各信号绩效
# ========================================

def analyze_performance(df, signal_col, name, target_period):
    """分析信号绩效"""
    signals = df[df[signal_col]]
    if len(signals) == 0:
        print(f"{name}: 无信号")
        return None

    print(f"\n{name}:")
    print(f"  信号数: {len(signals)}")

    results = {}
    for period in [12, 24, 48, 72]:
        fwd_col = f'fwd_ret_{period}h'
        returns = signals[fwd_col].dropna()
        if len(returns) > 0:
            win_rate = (returns > 0).mean() * 100
            mean_ret = returns.mean()
            marker = " <--" if period == target_period else ""
            print(f"  {period}H: 收益{mean_ret:.2f}%, 胜率{win_rate:.1f}% (n={len(returns)}){marker}")
            results[period] = {'win_rate': win_rate, 'mean_ret': mean_ret, 'n': len(returns)}

    return results


print("\n" + "="*60)
print("各信号绩效分析:")
print("="*60)

perf_25 = analyze_performance(eth, 'sig_25', '研究25 (目标72H胜率100%)', 72)
perf_27 = analyze_performance(eth, 'sig_27', '研究27 (目标72H胜率82.6%)', 72)
perf_29 = analyze_performance(eth, 'sig_29', '研究29 (目标12H胜率87.5%)', 12)
perf_30 = analyze_performance(eth, 'sig_30', '研究30 (目标24H胜率83.3%)', 24)


# ========================================
# 7. 信号时间窗口重叠分析
# ========================================

print("\n" + "="*60)
print("信号时间窗口重叠分析:")
print("="*60)

# 考虑到不同信号有不同的最佳持有期，我们检查时间窗口内的重叠
# 如果信号A触发后24H内有信号B触发，视为"共振"

def check_time_window_overlap(df, sig_a, sig_b, window_hours=24):
    """检查两个信号在时间窗口内的重叠"""
    sig_a_times = df[df[sig_a]].index
    sig_b_times = df[df[sig_b]].index

    overlaps = []
    for t_a in sig_a_times:
        for t_b in sig_b_times:
            diff_hours = abs((t_a - t_b).total_seconds()) / 3600
            if diff_hours <= window_hours and diff_hours > 0:
                overlaps.append((t_a, t_b, diff_hours))

    return overlaps


sig_pairs = [
    ('sig_25', 'sig_27'), ('sig_25', 'sig_29'), ('sig_25', 'sig_30'),
    ('sig_27', 'sig_29'), ('sig_27', 'sig_30'), ('sig_29', 'sig_30')
]

print("\n24H内时间窗口重叠:")
for sig_a, sig_b in sig_pairs:
    overlaps = check_time_window_overlap(eth, sig_a, sig_b, 24)
    if overlaps:
        print(f"  {sig_a} <-> {sig_b}: {len(overlaps)}次重叠")
        for t_a, t_b, diff in overlaps[:3]:
            print(f"    {t_a} <-> {t_b} (间隔{diff:.1f}H)")


# ========================================
# 8. 放宽条件的投票系统
# ========================================

print("\n" + "="*60)
print("放宽条件的投票系统:")
print("="*60)

# 创建每个信号的"有效区间"，在信号触发后的一段时间内视为有效
def create_signal_window(df, signal_col, window_hours):
    """创建信号的有效窗口"""
    signal_times = df[df[signal_col]].index
    window = pd.Series(False, index=df.index)

    for t in signal_times:
        start = t
        end = t + timedelta(hours=window_hours)
        mask = (df.index >= start) & (df.index <= end)
        window.loc[mask] = True

    return window

# 各信号的有效窗口
eth['win_25'] = create_signal_window(eth, 'sig_25', 24)  # 研究25触发后24H内有效
eth['win_27'] = create_signal_window(eth, 'sig_27', 24)
eth['win_29'] = create_signal_window(eth, 'sig_29', 12)  # 研究29只有12H有效
eth['win_30'] = create_signal_window(eth, 'sig_30', 24)

# 计算窗口重叠数
eth['window_overlap'] = (eth['win_25'].astype(int) +
                         eth['win_27'].astype(int) +
                         eth['win_29'].astype(int) +
                         eth['win_30'].astype(int))

print("\n窗口重叠分布:")
print(eth['window_overlap'].value_counts().sort_index())

# 分析窗口重叠>=2的时段
overlap_2 = eth[eth['window_overlap'] >= 2]
if len(overlap_2) > 0:
    print(f"\n窗口重叠>=2的时段: {len(overlap_2)}小时")

    # 找到这些时段的起始点
    overlap_starts = []
    prev_in_overlap = False
    for t, row in eth.iterrows():
        if row['window_overlap'] >= 2 and not prev_in_overlap:
            overlap_starts.append(t)
        prev_in_overlap = row['window_overlap'] >= 2

    print(f"共{len(overlap_starts)}个重叠起始点:")
    for t in overlap_starts[:10]:
        close = eth.loc[t, 'close']
        fwd_24 = eth.loc[t, 'fwd_ret_24h']
        fwd_72 = eth.loc[t, 'fwd_ret_72h']
        print(f"  {t}: close={close:.2f}, 24H收益={fwd_24:.2f}%, 72H收益={fwd_72:.2f}%")


# ========================================
# 9. 综合投票策略
# ========================================

print("\n" + "="*60)
print("综合投票策略:")
print("="*60)

# 策略1: 任一信号触发
any_signal = eth['sig_25'] | eth['sig_27'] | eth['sig_29'] | eth['sig_30']
any_signal_clean = remove_overlap_signals(any_signal, 24)
signals = eth[any_signal_clean]
print(f"\n策略1: 任一信号 ({len(signals)}个信号)")
for period in [12, 24, 48, 72]:
    returns = signals[f'fwd_ret_{period}h'].dropna()
    if len(returns) > 0:
        print(f"  {period}H: 收益{returns.mean():.2f}%, 胜率{(returns>0).mean()*100:.1f}%")

# 策略2: 熊市确认 (MA50<MA200) + 任一信号
bear_confirm = eth['MA50'] < eth['MA200']
bear_signal = any_signal & bear_confirm
bear_signal_clean = remove_overlap_signals(bear_signal, 24)
signals = eth[bear_signal_clean]
print(f"\n策略2: 熊市确认+任一信号 ({len(signals)}个信号)")
for period in [12, 24, 48, 72]:
    returns = signals[f'fwd_ret_{period}h'].dropna()
    if len(returns) > 0:
        print(f"  {period}H: 收益{returns.mean():.2f}%, 胜率{(returns>0).mean()*100:.1f}%")

# 策略3: 研究29+研究30组合 (看起来这两个信号比较稳定)
sig_29_30 = eth['sig_29'] | eth['sig_30']
sig_29_30_clean = remove_overlap_signals(sig_29_30, 24)
signals = eth[sig_29_30_clean]
print(f"\n策略3: 研究29+研究30组合 ({len(signals)}个信号)")
for period in [12, 24, 48, 72]:
    returns = signals[f'fwd_ret_{period}h'].dropna()
    if len(returns) > 0:
        print(f"  {period}H: 收益{returns.mean():.2f}%, 胜率{(returns>0).mean()*100:.1f}%")


# ========================================
# 10. 信号质量分析
# ========================================

print("\n" + "="*60)
print("信号质量深入分析:")
print("="*60)

# 分析每个信号触发时的市场状态
def analyze_signal_context(df, signal_col, name):
    """分析信号触发时的市场环境"""
    signals = df[df[signal_col]]
    if len(signals) == 0:
        return

    print(f"\n{name}信号触发时的市场状态:")
    print(f"  平均24H涨幅: {signals['ret_24h'].mean():.2f}%")
    print(f"  平均RSI: {signals['RSI'].mean():.1f}")
    print(f"  MA50<MA200占比: {(signals['MA50'] < signals['MA200']).mean()*100:.1f}%")
    print(f"  平均成交量/均量: {(signals['volume']/signals['vol_ma20']).mean():.2f}x")

    # 分析信号后的走势
    fwd_24_positive = (signals['fwd_ret_24h'] > 0).mean() * 100
    fwd_72_positive = (signals['fwd_ret_72h'] > 0).mean() * 100
    print(f"  24H做空胜率: {fwd_24_positive:.1f}%")
    print(f"  72H做空胜率: {fwd_72_positive:.1f}%")


analyze_signal_context(eth, 'sig_25', '研究25')
analyze_signal_context(eth, 'sig_27', '研究27')
analyze_signal_context(eth, 'sig_29', '研究29')
analyze_signal_context(eth, 'sig_30', '研究30')


# ========================================
# 11. 输出信号明细
# ========================================

print("\n" + "="*60)
print("研究29+研究30信号明细:")
print("="*60)

sig_29_30_signals = eth[sig_29_30_clean][['close', 'ret_24h', 'RSI',
                                          'sig_29', 'sig_30',
                                          'fwd_ret_12h', 'fwd_ret_24h', 'fwd_ret_48h', 'fwd_ret_72h']]
print(sig_29_30_signals.to_string())


# ========================================
# 12. 年度分布
# ========================================

print("\n" + "="*60)
print("年度分布:")
print("="*60)

eth['year'] = eth.index.year
for sig_name in ['sig_25', 'sig_27', 'sig_29', 'sig_30']:
    yearly = eth[eth[sig_name]].groupby('year').size()
    print(f"\n{sig_name}:")
    print(yearly.to_string())


print("\n" + "="*60)
print("研究31 v2完成")
print("="*60)
