# -*- coding: utf-8 -*-
"""
【CTA-ETH-研究14】支撑位做多信号研究

研究目标:
研究价格在关键支撑位(均线、前低、整数关口等)获得支撑后的做多信号。

研究方向:
1. 均线支撑(MA20/MA50/MA100/MA200)
2. 前期低点支撑(回踩不破)
3. 多次测试同一支撑位
4. 支撑位+放量确认反弹

与研究9对比:
研究9关注的是"回调+反弹确认"，本研究专注于"支撑位"概念的精确定义和验证。
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

print("加载数据...")
with open(data_path, 'rb') as f:
    swap_dict = pickle.load(f)

eth = swap_dict['ETH-USDT'].copy()
eth = eth.dropna(subset=['close'])
eth = eth.reset_index(drop=True)

print(f"ETH有效数据: {len(eth)} 行")
print(f"时间范围: {eth['candle_begin_time'].min()} 至 {eth['candle_begin_time'].max()}")

# =============================================================================
# 2. 计算未来收益和基础指标
# =============================================================================
print("\n计算基础指标...")

# 未来收益
for h in [12, 24, 48, 72]:
    eth[f'future_{h}h'] = eth['close'].shift(-h) / eth['close'] - 1

# 均线
for ma in [20, 50, 100, 120, 200]:
    eth[f'ma{ma}'] = eth['close'].rolling(ma, min_periods=1).mean()

# 成交量指标
eth['vol_ma24'] = eth['volume'].rolling(24).mean()
eth['vol_ratio'] = eth['volume'] / eth['vol_ma24']
eth['quote_vol_ma24'] = eth['quote_volume'].rolling(24).mean()
eth['quote_vol_ratio'] = eth['quote_volume'] / eth['quote_vol_ma24']

# 价格变动
eth['price_chg_1h'] = eth['close'] / eth['close'].shift(1) - 1
eth['price_chg_4h'] = eth['close'] / eth['close'].shift(4) - 1
eth['price_chg_24h'] = eth['close'] / eth['close'].shift(24) - 1

# 48H内回撤
eth['high_48h'] = eth['high'].rolling(48, min_periods=1).max()
eth['drawdown_48h'] = eth['close'] / eth['high_48h'] - 1

# 距离各均线的距离
for ma in [20, 50, 100, 200]:
    eth[f'dist_ma{ma}'] = eth['close'] / eth[f'ma{ma}'] - 1

# 前N日低点
for n in [20, 50, 100]:
    n_hours = n * 24
    eth[f'low_{n}d'] = eth['low'].rolling(n_hours, min_periods=1).min()
    eth[f'dist_low_{n}d'] = eth['close'] / eth[f'low_{n}d'] - 1

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

    print(f"\n{'='*70}")
    print(f"【{name}】")
    print(f"信号次数: {stats['signal_count']}, 信号占比: {stats['signal_ratio']:.2f}%")
    print(f"{'持有':<6} {'平均收益':<10} {'中位数':<10} {'胜率':<8} {'夏普':<8}")
    for h in [12, 24, 48, 72]:
        if f'{h}h_mean' in stats:
            print(f"{h}H      {stats[f'{h}h_mean']:>8.2f}%  {stats[f'{h}h_median']:>8.2f}%  {stats[f'{h}h_winrate']:>6.1f}%  {stats[f'{h}h_sharpe']:>7.2f}")

def print_compact_stats(name, stats):
    """紧凑打印统计结果"""
    if stats is None:
        print(f"{name:<50} 无信号")
        return

    print(f"{name:<50} N={stats['signal_count']:<4} 48H={stats.get('48h_mean', 0):>6.2f}%  胜率={stats.get('48h_winrate', 0):>5.1f}%  夏普={stats.get('48h_sharpe', 0):>6.2f}")

# =============================================================================
# 4. 研究1: 均线支撑信号
# =============================================================================
print("\n" + "="*80)
print("研究1: 均线支撑信号")
print("="*80)

# 定义"触碰均线获得支撑"的条件:
# 1. 价格从上方触碰均线（低点接近或穿过均线）
# 2. 收盘价仍在均线上方（没有跌破）
# 3. 有反弹迹象

print("\n--- 1.1 基础均线支撑 (价格触碰均线后反弹) ---")

for ma in [20, 50, 100, 200]:
    ma_col = f'ma{ma}'

    # 条件: 低点穿过均线，但收盘在均线上方，说明获得支撑
    eth[f'touch_ma{ma}'] = (
        (eth['low'] <= eth[ma_col] * 1.01) &  # 低点接近或触及均线
        (eth['close'] > eth[ma_col]) &          # 收盘在均线上方
        (eth['close'] > eth['open'])             # 当前为阳线
    ).astype(int)

    stats = calc_signal_stats(eth, f'touch_ma{ma}')
    print_compact_stats(f"触碰MA{ma}获得支撑", stats)

print("\n--- 1.2 均线支撑 + 放量确认 ---")

for ma in [20, 50, 100, 200]:
    for vol_mult in [1.5, 2.0, 2.5]:
        eth[f'touch_ma{ma}_vol{vol_mult}'] = (
            (eth[f'touch_ma{ma}'] == 1) &
            (eth['vol_ratio'] >= vol_mult)
        ).astype(int)

        stats = calc_signal_stats(eth, f'touch_ma{ma}_vol{vol_mult}')
        print_compact_stats(f"触碰MA{ma}+放量{vol_mult}x", stats)

print("\n--- 1.3 均线支撑 + 趋势过滤 ---")

# 只在上升趋势中买入均线支撑
for ma in [50, 100, 200]:
    # 趋势条件: 短期均线在长期均线之上
    trend_cond = eth['ma20'] > eth[f'ma{ma}']

    eth[f'touch_ma{ma}_trend'] = (
        (eth[f'touch_ma{ma}'] == 1) &
        trend_cond
    ).astype(int)

    stats = calc_signal_stats(eth, f'touch_ma{ma}_trend')
    print_compact_stats(f"触碰MA{ma}+MA20>MA{ma}", stats)

print("\n--- 1.4 均线支撑 + 较强反弹 ---")

# 要求当根K线有较强反弹
for ma in [50, 100, 200]:
    for bounce in [1.0, 1.5, 2.0]:
        bounce_pct = bounce / 100
        eth[f'touch_ma{ma}_bounce{bounce}'] = (
            (eth['low'] <= eth[f'ma{ma}'] * 1.01) &
            (eth['close'] > eth[f'ma{ma}']) &
            ((eth['close'] - eth['low']) / eth['low'] >= bounce_pct)  # 从低点反弹至少bounce%
        ).astype(int)

        stats = calc_signal_stats(eth, f'touch_ma{ma}_bounce{bounce}')
        print_compact_stats(f"触碰MA{ma}+反弹{bounce}%", stats)

# =============================================================================
# 5. 研究2: 前期低点支撑
# =============================================================================
print("\n" + "="*80)
print("研究2: 前期低点支撑 (回踩不破)")
print("="*80)

print("\n--- 2.1 基础前低支撑 ---")

for n in [20, 50, 100]:
    n_hours = n * 24

    # 计算前N日低点（排除当前K线）
    eth[f'prev_low_{n}d'] = eth['low'].shift(1).rolling(n_hours, min_periods=24).min()

    # 条件: 低点接近前低，但收盘在前低上方
    eth[f'support_low_{n}d'] = (
        (eth['low'] <= eth[f'prev_low_{n}d'] * 1.02) &  # 低点接近前低(2%容差)
        (eth['close'] > eth[f'prev_low_{n}d']) &         # 收盘在前低上方
        (eth['close'] > eth['open'])                      # 阳线
    ).astype(int)

    stats = calc_signal_stats(eth, f'support_low_{n}d')
    print_compact_stats(f"回踩{n}日前低获得支撑", stats)

print("\n--- 2.2 前低支撑 + 放量 ---")

for n in [20, 50]:
    for vol_mult in [1.5, 2.0, 2.5]:
        eth[f'support_low_{n}d_vol{vol_mult}'] = (
            (eth[f'support_low_{n}d'] == 1) &
            (eth['vol_ratio'] >= vol_mult)
        ).astype(int)

        stats = calc_signal_stats(eth, f'support_low_{n}d_vol{vol_mult}')
        print_compact_stats(f"回踩{n}日前低+放量{vol_mult}x", stats)

print("\n--- 2.3 前低支撑 + 趋势过滤 ---")

for n in [20, 50]:
    eth[f'support_low_{n}d_trend'] = (
        (eth[f'support_low_{n}d'] == 1) &
        (eth['ma20'] > eth['ma50'])  # 趋势向上
    ).astype(int)

    stats = calc_signal_stats(eth, f'support_low_{n}d_trend')
    print_compact_stats(f"回踩{n}日前低+均线多头", stats)

# =============================================================================
# 6. 研究3: 多次测试同一支撑位
# =============================================================================
print("\n" + "="*80)
print("研究3: 多次测试同一支撑位")
print("="*80)

print("\n--- 3.1 定义支撑区域并计算测试次数 ---")

# 使用滚动窗口内的低点作为"支撑区域"
# 每次价格接近这个区域都算一次测试

for n in [20, 50]:
    n_hours = n * 24

    # 计算支撑区域（过去N日的低点）
    eth[f'support_zone_{n}d'] = eth['low'].shift(1).rolling(n_hours, min_periods=24).min()

    # 定义"测试支撑"：低点进入支撑区域的2%范围内
    eth[f'test_support_{n}d'] = (
        eth['low'] <= eth[f'support_zone_{n}d'] * 1.02
    ).astype(int)

    # 计算过去N日内测试次数
    eth[f'test_count_{n}d'] = eth[f'test_support_{n}d'].rolling(n_hours, min_periods=1).sum()

print("\n--- 3.2 多次测试后获得支撑 ---")

for n in [20, 50]:
    for test_count in [2, 3, 4]:
        # 条件: 过去N日内已测试>=test_count次，当前再次测试并获得支撑
        eth[f'multi_test_{n}d_{test_count}x'] = (
            (eth[f'test_count_{n}d'] >= test_count) &
            (eth['low'] <= eth[f'support_zone_{n}d'] * 1.02) &
            (eth['close'] > eth[f'support_zone_{n}d']) &
            (eth['close'] > eth['open'])
        ).astype(int)

        stats = calc_signal_stats(eth, f'multi_test_{n}d_{test_count}x')
        print_compact_stats(f"{n}日内测试>={test_count}次+支撑有效", stats)

print("\n--- 3.3 多次测试 + 放量 ---")

for n in [20, 50]:
    for test_count in [2, 3]:
        for vol_mult in [1.5, 2.0]:
            eth[f'multi_test_{n}d_{test_count}x_vol{vol_mult}'] = (
                (eth[f'multi_test_{n}d_{test_count}x'] == 1) &
                (eth['vol_ratio'] >= vol_mult)
            ).astype(int)

            stats = calc_signal_stats(eth, f'multi_test_{n}d_{test_count}x_vol{vol_mult}')
            print_compact_stats(f"{n}日测试>={test_count}次+放量{vol_mult}x", stats)

# =============================================================================
# 7. 研究4: 支撑位 + 放量确认反弹
# =============================================================================
print("\n" + "="*80)
print("研究4: 支撑位 + 放量确认反弹（综合信号）")
print("="*80)

print("\n--- 4.1 均线支撑 + 强势反弹 ---")

# 综合信号: 触碰重要均线 + 放量 + 强反弹
for ma in [50, 100, 200]:
    eth[f'strong_support_ma{ma}'] = (
        (eth['low'] <= eth[f'ma{ma}'] * 1.01) &      # 触碰均线
        (eth['close'] > eth[f'ma{ma}']) &             # 收盘在均线上
        (eth['close'] > eth['open']) &                 # 阳线
        ((eth['close'] - eth['low']) / eth['low'] >= 0.015) &  # 从低点反弹>=1.5%
        (eth['vol_ratio'] >= 1.5)                      # 放量
    ).astype(int)

    stats = calc_signal_stats(eth, f'strong_support_ma{ma}')
    print_compact_stats(f"强势MA{ma}支撑(触碰+反弹1.5%+放量1.5x)", stats)

print("\n--- 4.2 加入趋势过滤 ---")

for ma in [50, 100, 200]:
    eth[f'strong_support_ma{ma}_trend'] = (
        (eth[f'strong_support_ma{ma}'] == 1) &
        (eth['ma20'] > eth[f'ma{ma}'])  # 短期均线在长期均线之上
    ).astype(int)

    stats = calc_signal_stats(eth, f'strong_support_ma{ma}_trend')
    print_compact_stats(f"强势MA{ma}支撑+趋势向上", stats)

print("\n--- 4.3 增强条件测试 ---")

# 测试更严格的条件
for ma in [50, 100]:
    for bounce in [2.0, 2.5, 3.0]:
        for vol in [2.0, 2.5]:
            eth[f'enhanced_ma{ma}_b{bounce}_v{vol}'] = (
                (eth['low'] <= eth[f'ma{ma}'] * 1.01) &
                (eth['close'] > eth[f'ma{ma}']) &
                (eth['close'] > eth['open']) &
                ((eth['close'] - eth['low']) / eth['low'] >= bounce/100) &
                (eth['vol_ratio'] >= vol) &
                (eth['ma20'] > eth[f'ma{ma}'])
            ).astype(int)

            stats = calc_signal_stats(eth, f'enhanced_ma{ma}_b{bounce}_v{vol}')
            if stats and stats['signal_count'] >= 10:
                print_compact_stats(f"MA{ma}支撑+反弹{bounce}%+放量{vol}x+趋势", stats)

# =============================================================================
# 8. 研究5: 与研究9对比
# =============================================================================
print("\n" + "="*80)
print("研究5: 与研究9回调反弹策略对比")
print("="*80)

# 复现研究9的最优策略
eth['high_20d'] = eth['high'].rolling(20*24, min_periods=1).max()
eth['research9_signal'] = (
    (eth['drawdown_48h'] <= -0.07) &           # 48H回撤>=7%
    (eth['price_chg_4h'] >= 0.015) &            # 4H动量>=1.5%
    (eth['ma20'] > eth['ma50']) &               # MA20>MA50
    (eth['close'] > eth['ma120']) &             # 价格>MA120
    (eth['close'] >= eth['high_20d'] * 0.85)   # 在20日高点85%以上
).astype(int)

stats_r9 = calc_signal_stats(eth, 'research9_signal')
print_stats("研究9基准: 回调反弹策略", stats_r9)

# 测试本研究最佳信号
print("\n本研究最佳信号:")
best_signals = [
    'touch_ma50_trend',
    'touch_ma100_bounce2.0',
    'strong_support_ma50_trend',
    'strong_support_ma100_trend',
]

for sig in best_signals:
    if sig in eth.columns:
        stats = calc_signal_stats(eth, sig)
        print_stats(sig, stats)

# =============================================================================
# 9. 研究6: 组合优化
# =============================================================================
print("\n" + "="*80)
print("研究6: 组合优化")
print("="*80)

print("\n--- 6.1 支撑信号 + 研究9条件组合 ---")

# 将支撑信号与研究9的趋势条件结合
for ma in [50, 100]:
    # 基础支撑 + 研究9的趋势条件
    eth[f'combined_ma{ma}_r9'] = (
        (eth['low'] <= eth[f'ma{ma}'] * 1.01) &
        (eth['close'] > eth[f'ma{ma}']) &
        (eth['close'] > eth['open']) &
        (eth['ma20'] > eth['ma50']) &
        (eth['close'] > eth['ma120'])
    ).astype(int)

    stats = calc_signal_stats(eth, f'combined_ma{ma}_r9')
    print_compact_stats(f"MA{ma}支撑+MA20>MA50+价格>MA120", stats)

print("\n--- 6.2 支撑信号 + 回撤条件 ---")

# 支撑信号需要有一定回撤背景
for ma in [50, 100]:
    for dd in [-0.03, -0.05, -0.07]:
        eth[f'support_ma{ma}_dd{abs(dd)}'] = (
            (eth['low'] <= eth[f'ma{ma}'] * 1.01) &
            (eth['close'] > eth[f'ma{ma}']) &
            (eth['close'] > eth['open']) &
            (eth['drawdown_48h'] <= dd) &
            (eth['ma20'] > eth['ma50'])
        ).astype(int)

        stats = calc_signal_stats(eth, f'support_ma{ma}_dd{abs(dd)}')
        print_compact_stats(f"MA{ma}支撑+48H回撤>={abs(dd)*100:.0f}%+趋势", stats)

print("\n--- 6.3 最终优化信号 ---")

# 综合最优条件
eth['final_support_signal'] = (
    (eth['low'] <= eth['ma50'] * 1.01) &           # 触碰MA50
    (eth['close'] > eth['ma50']) &                  # 收盘在MA50上
    (eth['close'] > eth['open']) &                   # 阳线
    ((eth['close'] - eth['low']) / eth['low'] >= 0.01) &  # 从低点反弹>=1%
    (eth['vol_ratio'] >= 1.5) &                      # 放量
    (eth['ma20'] > eth['ma50']) &                    # 趋势向上
    (eth['close'] > eth['ma120'])                    # 处于上升趋势
).astype(int)

eth['final_support_signal_v2'] = (
    (eth['low'] <= eth['ma100'] * 1.01) &           # 触碰MA100
    (eth['close'] > eth['ma100']) &                  # 收盘在MA100上
    (eth['close'] > eth['open']) &                   # 阳线
    ((eth['close'] - eth['low']) / eth['low'] >= 0.015) &  # 从低点反弹>=1.5%
    (eth['vol_ratio'] >= 1.5) &                      # 放量
    (eth['ma20'] > eth['ma50']) &                    # 趋势向上
    (eth['close'] > eth['ma120'])                    # 处于上升趋势
).astype(int)

eth['final_support_signal_v3'] = (
    ((eth['low'] <= eth['ma50'] * 1.01) | (eth['low'] <= eth['ma100'] * 1.01)) &  # 触碰MA50或MA100
    (eth['close'] > eth['ma50'].where(eth['low'] <= eth['ma50'] * 1.01, eth['ma100'])) &  # 收盘在对应均线上
    (eth['close'] > eth['open']) &                   # 阳线
    ((eth['close'] - eth['low']) / eth['low'] >= 0.02) &  # 从低点反弹>=2%
    (eth['vol_ratio'] >= 2.0) &                      # 放量2x
    (eth['ma20'] > eth['ma50']) &                    # 趋势向上
    (eth['drawdown_48h'] <= -0.03)                   # 有一定回撤背景
).astype(int)

print_stats("最终优化V1: MA50支撑+放量1.5x+趋势", calc_signal_stats(eth, 'final_support_signal'))
print_stats("最终优化V2: MA100支撑+反弹1.5%+放量1.5x+趋势", calc_signal_stats(eth, 'final_support_signal_v2'))
print_stats("最终优化V3: MA50/100支撑+反弹2%+放量2x+回撤", calc_signal_stats(eth, 'final_support_signal_v3'))

# =============================================================================
# 10. 年度稳健性检验
# =============================================================================
print("\n" + "="*80)
print("年度稳健性检验")
print("="*80)

eth['year'] = pd.to_datetime(eth['candle_begin_time']).dt.year

# 测试最佳信号的年度表现
test_signals = ['final_support_signal', 'final_support_signal_v2', 'strong_support_ma50_trend', 'research9_signal']

for sig_name in test_signals:
    if sig_name in eth.columns and eth[sig_name].sum() > 0:
        print(f"\n{sig_name} 年度检验:")
        print("-" * 50)
        for year in sorted(eth['year'].unique()):
            mask = (eth['year'] == year) & (eth[sig_name] == 1)
            ret = eth.loc[mask, 'future_48h'].dropna()
            if len(ret) >= 3:
                print(f"{year}年: 信号数={len(ret):<4}, 48H收益={ret.mean()*100:>6.2f}%, 胜率={(ret>0).mean()*100:.1f}%")

# =============================================================================
# 11. 最优信号汇总
# =============================================================================
print("\n" + "="*80)
print("最优信号汇总 (按48H收益排序)")
print("="*80)

# 收集所有信号的统计
all_signals = []
signal_cols = [col for col in eth.columns if
               col.startswith(('touch_', 'support_', 'multi_test_', 'strong_support_',
                               'enhanced_', 'combined_', 'final_'))]

for col in signal_cols:
    if eth[col].sum() >= 10:  # 至少10次信号
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

print(f"\n{'信号':<55} {'次数':<8} {'48H收益':<10} {'胜率':<8} {'夏普':<8}")
print("-" * 90)
for s in all_signals[:25]:
    print(f"{s['signal']:<55} {s['count']:<8} {s['48h_return']:>7.2f}%  {s['48h_winrate']:>6.1f}%  {s['48h_sharpe']:>7.2f}")

# =============================================================================
# 12. 研究总结
# =============================================================================
print("\n" + "="*80)
print("研究总结")
print("="*80)

# 研究9基准
stats_r9 = calc_signal_stats(eth, 'research9_signal')
if stats_r9:
    print(f"\n研究9基准: 信号数={stats_r9['signal_count']}, 48H收益={stats_r9['48h_mean']:.2f}%, 胜率={stats_r9['48h_winrate']:.1f}%")

# 本研究最优
if all_signals:
    best = all_signals[0]
    print(f"本研究最优: {best['signal']}")
    print(f"  信号数={best['count']}, 48H收益={best['48h_return']:.2f}%, 胜率={best['48h_winrate']:.1f}%, 夏普={best['48h_sharpe']:.2f}")

print("\n研究完成!")
