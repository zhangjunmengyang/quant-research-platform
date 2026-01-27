# -*- coding: utf-8 -*-
"""
【CTA-ETH-研究8】突破新高做多信号研究
研究价格突破N日新高作为做多信号的效果，探索"强者恒强"的逻辑在ETH上是否有效。
"""

import pickle
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# 1. 数据加载
# =============================================================================
data_path = "/Users/zhangjunmengyang/Downloads/coin-binance-spot-swap-preprocess-pkl-1h-2026-01-19/swap_dict.pkl"

with open(data_path, 'rb') as f:
    swap_dict = pickle.load(f)

eth = swap_dict['ETH-USDT'].copy()
eth = eth.dropna(subset=['close'])
eth = eth.reset_index(drop=True)

print(f"ETH有效数据: {len(eth)} 行")
print(f"时间范围: {eth['candle_begin_time'].min()} 至 {eth['candle_begin_time'].max()}")

# =============================================================================
# 2. 计算未来收益
# =============================================================================
for h in [12, 24, 48, 72]:
    eth[f'future_{h}h'] = eth['close'].shift(-h) / eth['close'] - 1

# =============================================================================
# 3. 辅助函数
# =============================================================================
def calc_signal_stats(df, signal_col, holding_hours=[12, 24, 48, 72]):
    """计算信号统计"""
    signal_df = df[df[signal_col] == 1].copy()

    if len(signal_df) == 0:
        return None

    results = {
        'signal_count': len(signal_df),
        'signal_ratio': len(signal_df) / len(df) * 100
    }

    for h in holding_hours:
        col = f'future_{h}h'
        if col in signal_df.columns:
            returns = signal_df[col].dropna()
            if len(returns) > 0:
                results[f'{h}h_mean'] = returns.mean() * 100
                results[f'{h}h_median'] = returns.median() * 100
                results[f'{h}h_std'] = returns.std() * 100
                results[f'{h}h_winrate'] = (returns > 0).mean() * 100
                results[f'{h}h_sharpe'] = returns.mean() / returns.std() * np.sqrt(365*24/h) if returns.std() > 0 else 0

    return results

def print_stats(name, stats):
    """打印统计结果"""
    if stats is None:
        print(f"{name}: 无信号")
        return

    print(f"\n{'='*60}")
    print(f"【{name}】")
    print(f"信号次数: {stats['signal_count']}, 信号占比: {stats['signal_ratio']:.2f}%")
    print(f"{'持有':<6} {'平均收益':<10} {'中位数':<10} {'胜率':<8} {'夏普':<8}")
    for h in [12, 24, 48, 72]:
        if f'{h}h_mean' in stats:
            print(f"{h}H      {stats[f'{h}h_mean']:>8.2f}%  {stats[f'{h}h_median']:>8.2f}%  {stats[f'{h}h_winrate']:>6.1f}%  {stats[f'{h}h_sharpe']:>7.2f}")

# =============================================================================
# 4. 研究1: 突破N日新高信号 (N=20,50,100,200)
# =============================================================================
print("\n" + "="*80)
print("研究1: 突破N日新高信号")
print("="*80)

# N日 = N*24小时 (1小时数据)
n_days_list = [5, 10, 20, 50, 100, 200]

for n_days in n_days_list:
    n_hours = n_days * 24
    # 突破N日新高: 当前收盘价 > 过去N日最高价
    eth[f'high_{n_days}d'] = eth['high'].shift(1).rolling(n_hours, min_periods=1).max()
    eth[f'break_high_{n_days}d'] = (eth['close'] > eth[f'high_{n_days}d']).astype(int)

    stats = calc_signal_stats(eth, f'break_high_{n_days}d')
    print_stats(f"突破{n_days}日新高", stats)

# =============================================================================
# 5. 研究2: 突破新高 + 放量确认
# =============================================================================
print("\n" + "="*80)
print("研究2: 突破新高 + 放量确认")
print("="*80)

# 计算成交量倍数
eth['vol_ma24'] = eth['volume'].rolling(24).mean()
eth['vol_ratio'] = eth['volume'] / eth['vol_ma24']

# 测试不同参数组合
for n_days in [20, 50]:
    n_hours = n_days * 24
    for vol_mult in [2.0, 2.5, 3.0, 3.5]:
        eth[f'break_{n_days}d_vol{vol_mult}'] = (
            (eth[f'break_high_{n_days}d'] == 1) &
            (eth['vol_ratio'] >= vol_mult)
        ).astype(int)

        stats = calc_signal_stats(eth, f'break_{n_days}d_vol{vol_mult}')
        print_stats(f"突破{n_days}日新高 + 放量{vol_mult}x", stats)

# =============================================================================
# 6. 研究3: 首次突破 vs 持续突破
# =============================================================================
print("\n" + "="*80)
print("研究3: 首次突破 vs 持续突破")
print("="*80)

for n_days in [20, 50]:
    # 首次突破: 昨日未突破，今日突破
    eth[f'first_break_{n_days}d'] = (
        (eth[f'break_high_{n_days}d'] == 1) &
        (eth[f'break_high_{n_days}d'].shift(1) == 0)
    ).astype(int)

    # 持续突破: 连续N个小时都在突破状态
    for cont_hours in [6, 12, 24]:
        eth[f'cont_break_{n_days}d_{cont_hours}h'] = (
            eth[f'break_high_{n_days}d'].rolling(cont_hours).sum() == cont_hours
        ).astype(int)

    stats = calc_signal_stats(eth, f'first_break_{n_days}d')
    print_stats(f"首次突破{n_days}日新高", stats)

    for cont_hours in [6, 12, 24]:
        stats = calc_signal_stats(eth, f'cont_break_{n_days}d_{cont_hours}h')
        print_stats(f"持续{cont_hours}H突破{n_days}日新高", stats)

# =============================================================================
# 7. 研究4: 突破幅度
# =============================================================================
print("\n" + "="*80)
print("研究4: 突破幅度研究")
print("="*80)

for n_days in [20, 50]:
    # 计算突破幅度
    eth[f'break_pct_{n_days}d'] = (eth['close'] / eth[f'high_{n_days}d'] - 1) * 100

    # 不同突破幅度阈值
    for pct in [0.5, 1.0, 2.0, 3.0]:
        eth[f'break_{n_days}d_pct{pct}'] = (
            eth[f'break_pct_{n_days}d'] >= pct
        ).astype(int)

        stats = calc_signal_stats(eth, f'break_{n_days}d_pct{pct}')
        print_stats(f"突破{n_days}日新高>{pct}%", stats)

# =============================================================================
# 8. 研究5: 突破新高 + 涨幅确认
# =============================================================================
print("\n" + "="*80)
print("研究5: 突破新高 + 当小时涨幅确认")
print("="*80)

# 计算当小时涨幅
eth['pct_change'] = (eth['close'] / eth['open'] - 1) * 100

for n_days in [20, 50]:
    for pct in [1.0, 2.0, 2.5, 3.0]:
        eth[f'break_{n_days}d_chg{pct}'] = (
            (eth[f'break_high_{n_days}d'] == 1) &
            (eth['pct_change'] >= pct)
        ).astype(int)

        stats = calc_signal_stats(eth, f'break_{n_days}d_chg{pct}')
        print_stats(f"突破{n_days}日新高 + 涨{pct}%", stats)

# =============================================================================
# 9. 研究6: 与研究7放量信号组合
# =============================================================================
print("\n" + "="*80)
print("研究6: 突破新高 + 研究7放量信号组合")
print("="*80)

# 研究7的核心信号: 放量3.5x + 涨2.5%
eth['research7_signal'] = (
    (eth['vol_ratio'] >= 3.5) &
    (eth['pct_change'] >= 2.5)
).astype(int)

# 计算EMA
eth['ema20'] = eth['close'].ewm(span=20, adjust=False).mean()

for n_days in [20, 50]:
    # 突破新高 + 研究7信号
    eth[f'break_{n_days}d_r7'] = (
        (eth[f'break_high_{n_days}d'] == 1) &
        (eth['research7_signal'] == 1)
    ).astype(int)

    stats = calc_signal_stats(eth, f'break_{n_days}d_r7')
    print_stats(f"突破{n_days}日新高 + 放量3.5x涨2.5%", stats)

    # 突破新高 + 放量 + EMA多头
    eth[f'break_{n_days}d_r7_ema'] = (
        (eth[f'break_high_{n_days}d'] == 1) &
        (eth['research7_signal'] == 1) &
        (eth['close'] > eth['ema20'])
    ).astype(int)

    stats = calc_signal_stats(eth, f'break_{n_days}d_r7_ema')
    print_stats(f"突破{n_days}日新高 + 放量3.5x涨2.5% + EMA20", stats)

# =============================================================================
# 10. 研究7: 新高频率统计
# =============================================================================
print("\n" + "="*80)
print("研究7: 新高频率 (过去N日内创新高次数)")
print("="*80)

for n_days in [20, 50]:
    n_hours = n_days * 24
    # 计算创新高次数
    eth[f'high_count_{n_days}d'] = eth[f'break_high_{n_days}d'].rolling(n_hours).sum()

    # 高频创新高 (多次创新高后继续做多)
    for threshold in [5, 10, 20]:
        eth[f'high_count_{n_days}d_gt{threshold}'] = (eth[f'high_count_{n_days}d'] >= threshold).astype(int)
        stats = calc_signal_stats(eth, f'high_count_{n_days}d_gt{threshold}')
        print_stats(f"{n_days}日内创新高>{threshold}次", stats)

# =============================================================================
# 11. 最优信号汇总
# =============================================================================
print("\n" + "="*80)
print("最优信号汇总 (按48H收益排序)")
print("="*80)

# 收集所有信号的统计
all_signals = []
signal_cols = [col for col in eth.columns if col.startswith(('break_', 'first_break_', 'cont_break_', 'high_count_'))]

for col in signal_cols:
    if eth[col].sum() > 10:  # 至少10次信号
        stats = calc_signal_stats(eth, col)
        if stats and '48h_mean' in stats and stats['48h_mean'] > 0:
            all_signals.append({
                'signal': col,
                'count': stats['signal_count'],
                '48h_return': stats['48h_mean'],
                '48h_winrate': stats['48h_winrate'],
                '48h_sharpe': stats['48h_sharpe']
            })

# 按48H收益排序
all_signals = sorted(all_signals, key=lambda x: x['48h_return'], reverse=True)

print(f"\n{'信号':<45} {'次数':<8} {'48H收益':<10} {'胜率':<8} {'夏普':<8}")
print("-" * 80)
for s in all_signals[:20]:
    print(f"{s['signal']:<45} {s['count']:<8} {s['48h_return']:>7.2f}%  {s['48h_winrate']:>6.1f}%  {s['48h_sharpe']:>7.2f}")

# =============================================================================
# 12. 对比研究7基准
# =============================================================================
print("\n" + "="*80)
print("对比研究7基准")
print("="*80)

# 计算MACD
eth['ema12'] = eth['close'].ewm(span=12, adjust=False).mean()
eth['ema26'] = eth['close'].ewm(span=26, adjust=False).mean()
eth['macd'] = eth['ema12'] - eth['ema26']
eth['macd_signal'] = eth['macd'].ewm(span=9, adjust=False).mean()
eth['macd_hist'] = eth['macd'] - eth['macd_signal']

# 研究7完整信号: 放量3.5x + 涨2.5% + EMA20多头 + MACD金叉
eth['research7_full'] = (
    (eth['vol_ratio'] >= 3.5) &
    (eth['pct_change'] >= 2.5) &
    (eth['close'] > eth['ema20']) &
    (eth['macd'] > eth['macd_signal'])
).astype(int)

stats_r7 = calc_signal_stats(eth, 'research7_full')
print_stats("研究7: 放量3.5x+涨2.5%+EMA+MACD", stats_r7)

# 与突破新高组合
eth['r7_break20'] = (
    (eth['research7_full'] == 1) &
    (eth['break_high_20d'] == 1)
).astype(int)

eth['r7_break50'] = (
    (eth['research7_full'] == 1) &
    (eth['break_high_50d'] == 1)
).astype(int)

stats_r7_b20 = calc_signal_stats(eth, 'r7_break20')
stats_r7_b50 = calc_signal_stats(eth, 'r7_break50')

print_stats("研究7 + 突破20日新高", stats_r7_b20)
print_stats("研究7 + 突破50日新高", stats_r7_b50)

print("\n研究完成!")
