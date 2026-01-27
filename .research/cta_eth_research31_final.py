"""
CTA-ETH-研究31: 做空信号投票融合研究 - 最终版

基于实际数据分析，重新设计做空信号融合策略
"""

import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import combinations

# ========================================
# 1. 加载数据
# ========================================

data_path = "/Users/zhangjunmengyang/Downloads/coin-binance-spot-swap-preprocess-pkl-1h-2026-01-19/swap_dict.pkl"

with open(data_path, 'rb') as f:
    swap_dict = pickle.load(f)

eth = swap_dict['ETH-USDT'].copy()
eth['candle_begin_time'] = pd.to_datetime(eth['candle_begin_time'])
eth = eth.set_index('candle_begin_time')
eth = eth[eth['close'].notna()].copy()

print(f"ETH数据: {eth.index[0]} ~ {eth.index[-1]}, 共{len(eth)}行")

# ========================================
# 2. 基础指标计算
# ========================================

# 均线
for period in [20, 50, 120, 200]:
    eth[f'MA{period}'] = eth['close'].rolling(period).mean()

# 日线/周线均线
eth['MA20_daily'] = eth['close'].rolling(20*24).mean()
eth['MA50_daily'] = eth['close'].rolling(50*24).mean()
eth['MA5_weekly'] = eth['close'].rolling(5*24*7).mean()
eth['MA10_weekly'] = eth['close'].rolling(10*24*7).mean()

# 成交量
eth['vol_ma10'] = eth['volume'].rolling(10).mean()
eth['vol_ma20'] = eth['volume'].rolling(20).mean()

# RSI
delta = eth['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / avg_loss
eth['RSI'] = 100 - (100 / (1 + rs))

# 区间涨幅
for h in [1, 4, 8, 12, 24, 48]:
    eth[f'ret_{h}h'] = eth['close'].pct_change(h) * 100

# 做空未来收益 (价格下跌为正)
for h in [12, 24, 48, 72]:
    eth[f'fwd_short_{h}h'] = -eth['close'].pct_change(-h) * 100

# 区间高低点
eth['high_12h'] = eth['high'].rolling(12).max()
eth['high_24h'] = eth['high'].rolling(24).max()
eth['low_24h'] = eth['low'].rolling(24).min()


# ========================================
# 3. 市场状态识别
# ========================================

# 熊市定义
eth['is_bear'] = eth['MA50'] < eth['MA200']
eth['is_strong_bear'] = eth['MA50'] < eth['MA120'] * 0.95

# 日周共振空头
eth['daily_bear'] = eth['MA20_daily'] < eth['MA50_daily']
eth['weekly_bear'] = eth['MA5_weekly'] < eth['MA10_weekly']
eth['multi_tf_bear'] = eth['daily_bear'] & eth['weekly_bear']


# ========================================
# 4. 定义做空信号条件
# ========================================

# 信号A: 熊市反弹做空 (反弹后RSI超买)
eth['sig_A'] = (
    eth['is_bear'] &
    (eth['ret_24h'] > 8) &
    (eth['RSI'] > 70)
)

# 信号B: 熊市恐慌放量 (恐慌抛售后追空)
eth['sig_B'] = (
    eth['is_bear'] &
    (eth['volume'] > 3 * eth['vol_ma20']) &
    (eth['ret_1h'] < -2) &
    (eth['ret_24h'] < -5)
)

# 信号C: 反弹衰竭 (反弹后出现回落)
rolling_high = eth['high'].rolling(12).max()
pullback = (rolling_high - eth['close']) / rolling_high * 100
eth['sig_C'] = (
    eth['is_bear'] &
    (eth['ret_12h'] > 5) &
    (pullback > 1.5)
)

# 信号D: 多周期共振做空
eth['sig_D'] = (
    eth['multi_tf_bear'] &
    (eth['ret_24h'] > 6) &
    (eth['RSI'] > 65)
)


# ========================================
# 5. 信号处理函数
# ========================================

def remove_overlap(signal_series, min_gap=24):
    """去除重叠信号"""
    signal_idx = signal_series[signal_series].index.tolist()
    if not signal_idx:
        return signal_series

    filtered = [signal_idx[0]]
    for idx in signal_idx[1:]:
        hours_diff = (idx - filtered[-1]).total_seconds() / 3600
        if hours_diff >= min_gap:
            filtered.append(idx)

    result = pd.Series(False, index=signal_series.index)
    result.loc[filtered] = True
    return result


def analyze_signal(df, signal_series, name):
    """分析单个信号的绩效"""
    if isinstance(signal_series, str):
        signals = df[df[signal_series]]
    else:
        signals = df[signal_series]
    if len(signals) == 0:
        return None

    results = {'name': name, 'count': len(signals)}
    for h in [12, 24, 48, 72]:
        returns = signals[f'fwd_short_{h}h'].dropna()
        if len(returns) > 0:
            results[f'{h}h_ret'] = returns.mean()
            results[f'{h}h_win'] = (returns > 0).mean() * 100

    return results


# ========================================
# 6. 去重并分析各信号
# ========================================

print("\n" + "="*70)
print("单信号分析:")
print("="*70)

signals = ['sig_A', 'sig_B', 'sig_C', 'sig_D']
signal_names = ['熊市反弹超买', '熊市恐慌放量', '反弹衰竭', '多周期共振']

for sig, name in zip(signals, signal_names):
    eth[f'{sig}_clean'] = remove_overlap(eth[sig], 24)
    result = analyze_signal(eth, f'{sig}_clean', name)
    if result:
        print(f"\n{name} ({sig}): {result['count']}个信号")
        for h in [12, 24, 48, 72]:
            if f'{h}h_ret' in result:
                print(f"  {h}H: 收益{result[f'{h}h_ret']:.2f}%, 胜率{result[f'{h}h_win']:.1f}%")


# ========================================
# 7. 投票融合分析
# ========================================

print("\n" + "="*70)
print("投票融合分析:")
print("="*70)

# 计算原始投票数
eth['vote'] = (eth['sig_A_clean'].astype(int) +
               eth['sig_B_clean'].astype(int) +
               eth['sig_C_clean'].astype(int) +
               eth['sig_D_clean'].astype(int))

print("\n投票分布:")
print(eth['vote'].value_counts().sort_index())

# 扩展时间窗口投票 (24H内触发视为同一信号)
def create_window(df, sig_col, hours):
    times = df[df[sig_col]].index
    window = pd.Series(False, index=df.index)
    for t in times:
        mask = (df.index >= t) & (df.index <= t + timedelta(hours=hours))
        window.loc[mask] = True
    return window

for sig in signals:
    eth[f'{sig}_win'] = create_window(eth, f'{sig}_clean', 24)

eth['vote_window'] = (eth['sig_A_win'].astype(int) +
                      eth['sig_B_win'].astype(int) +
                      eth['sig_C_win'].astype(int) +
                      eth['sig_D_win'].astype(int))

print("\n窗口投票分布:")
print(eth['vote_window'].value_counts().sort_index())


# ========================================
# 8. 组合策略测试
# ========================================

print("\n" + "="*70)
print("组合策略测试:")
print("="*70)

# 测试1: 任一信号
any_sig = eth['sig_A_clean'] | eth['sig_B_clean'] | eth['sig_C_clean'] | eth['sig_D_clean']
any_sig_clean = remove_overlap(any_sig, 24)
result = analyze_signal(eth, any_sig_clean, '任一信号')
if result:
    print(f"\n策略1: 任一信号触发 ({result['count']}个)")
    for h in [24, 48, 72]:
        print(f"  {h}H: 收益{result[f'{h}h_ret']:.2f}%, 胜率{result[f'{h}h_win']:.1f}%")

# 测试2: A+D组合 (反弹超买+多周期共振)
sig_AD = eth['sig_A_clean'] | eth['sig_D_clean']
sig_AD_clean = remove_overlap(sig_AD, 24)
result = analyze_signal(eth, sig_AD_clean, 'A+D')
if result:
    print(f"\n策略2: 反弹超买+多周期共振 ({result['count']}个)")
    for h in [24, 48, 72]:
        print(f"  {h}H: 收益{result[f'{h}h_ret']:.2f}%, 胜率{result[f'{h}h_win']:.1f}%")

# 测试3: C+D组合 (衰竭+共振)
sig_CD = eth['sig_C_clean'] | eth['sig_D_clean']
sig_CD_clean = remove_overlap(sig_CD, 24)
result = analyze_signal(eth, sig_CD_clean, 'C+D')
if result:
    print(f"\n策略3: 衰竭+多周期共振 ({result['count']}个)")
    for h in [24, 48, 72]:
        print(f"  {h}H: 收益{result[f'{h}h_ret']:.2f}%, 胜率{result[f'{h}h_win']:.1f}%")

# 测试4: 窗口>=2
win2 = eth['vote_window'] >= 2
win2_starts = []
prev = False
for t, v in eth['vote_window'].items():
    if v >= 2 and not prev:
        win2_starts.append(t)
    prev = v >= 2

if win2_starts:
    win2_df = eth.loc[win2_starts]
    print(f"\n策略4: 窗口重叠>=2 ({len(win2_starts)}个)")
    for h in [24, 48, 72]:
        returns = win2_df[f'fwd_short_{h}h'].dropna()
        if len(returns) > 0:
            print(f"  {h}H: 收益{returns.mean():.2f}%, 胜率{(returns>0).mean()*100:.1f}%")


# ========================================
# 9. 最优策略确定
# ========================================

print("\n" + "="*70)
print("策略评估与结论:")
print("="*70)

# 收集所有组合的绩效
all_results = []

# 单信号
for sig, name in zip(signals, signal_names):
    sigs = eth[eth[f'{sig}_clean']]
    if len(sigs) >= 5:
        for h in [24, 48, 72]:
            rets = sigs[f'fwd_short_{h}h'].dropna()
            if len(rets) >= 5:
                all_results.append({
                    'strategy': name,
                    'period': f'{h}H',
                    'count': len(rets),
                    'mean_ret': rets.mean(),
                    'win_rate': (rets > 0).mean() * 100,
                    'std': rets.std(),
                    'sharpe': rets.mean() / rets.std() if rets.std() > 0 else 0
                })

# 组合
combos = [
    ('A+B', eth['sig_A_clean'] | eth['sig_B_clean']),
    ('A+C', eth['sig_A_clean'] | eth['sig_C_clean']),
    ('A+D', eth['sig_A_clean'] | eth['sig_D_clean']),
    ('B+C', eth['sig_B_clean'] | eth['sig_C_clean']),
    ('B+D', eth['sig_B_clean'] | eth['sig_D_clean']),
    ('C+D', eth['sig_C_clean'] | eth['sig_D_clean']),
    ('A+B+C', eth['sig_A_clean'] | eth['sig_B_clean'] | eth['sig_C_clean']),
    ('A+B+D', eth['sig_A_clean'] | eth['sig_B_clean'] | eth['sig_D_clean']),
    ('A+C+D', eth['sig_A_clean'] | eth['sig_C_clean'] | eth['sig_D_clean']),
    ('B+C+D', eth['sig_B_clean'] | eth['sig_C_clean'] | eth['sig_D_clean']),
    ('ALL', eth['sig_A_clean'] | eth['sig_B_clean'] | eth['sig_C_clean'] | eth['sig_D_clean']),
]

for name, combo in combos:
    combo_clean = remove_overlap(combo, 24)
    sigs = eth[combo_clean]
    if len(sigs) >= 5:
        for h in [24, 48, 72]:
            rets = sigs[f'fwd_short_{h}h'].dropna()
            if len(rets) >= 5:
                all_results.append({
                    'strategy': f'组合{name}',
                    'period': f'{h}H',
                    'count': len(rets),
                    'mean_ret': rets.mean(),
                    'win_rate': (rets > 0).mean() * 100,
                    'std': rets.std(),
                    'sharpe': rets.mean() / rets.std() if rets.std() > 0 else 0
                })

# 排序输出
results_df = pd.DataFrame(all_results)
if len(results_df) > 0:
    print("\n按夏普比率排序的Top15策略:")
    top15 = results_df.nlargest(15, 'sharpe')
    print(top15[['strategy', 'period', 'count', 'mean_ret', 'win_rate', 'sharpe']].to_string(index=False))

    print("\n按胜率排序的Top10策略 (样本>=10):")
    filtered = results_df[results_df['count'] >= 10].nlargest(10, 'win_rate')
    print(filtered[['strategy', 'period', 'count', 'mean_ret', 'win_rate', 'sharpe']].to_string(index=False))


# ========================================
# 10. 信号明细输出
# ========================================

print("\n" + "="*70)
print("最优策略信号明细 (C+D组合 48H):")
print("="*70)

best_sig = remove_overlap(eth['sig_C_clean'] | eth['sig_D_clean'], 24)
best_df = eth[best_sig][['close', 'ret_24h', 'RSI', 'is_bear', 'multi_tf_bear',
                         'sig_C_clean', 'sig_D_clean',
                         'fwd_short_24h', 'fwd_short_48h', 'fwd_short_72h']]
print(best_df.to_string())


# ========================================
# 11. 年度分布
# ========================================

print("\n" + "="*70)
print("年度绩效分布:")
print("="*70)

eth['year'] = eth.index.year
best_signals = eth[best_sig]

yearly_perf = best_signals.groupby('year').agg({
    'fwd_short_48h': ['count', 'mean', lambda x: (x > 0).mean() * 100]
}).round(2)
yearly_perf.columns = ['信号数', '平均收益%', '胜率%']
print(yearly_perf)


print("\n" + "="*70)
print("研究31完成 - 做空信号投票融合研究")
print("="*70)
