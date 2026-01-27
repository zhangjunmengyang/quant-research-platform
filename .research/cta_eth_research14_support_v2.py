# -*- coding: utf-8 -*-
"""
【CTA-ETH-研究14】支撑位做多信号研究 - 深入分析

基于初步研究的发现进行深入分析:
1. 最优信号 support_ma100_dd0.07 (MA100支撑+48H回撤>=7%+趋势) 达到3.32%收益
2. 对比研究9的7.77%收益
3. 探索信号重叠度和互补性
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

# =============================================================================
# 2. 计算基础指标
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

# 价格变动
eth['price_chg_1h'] = eth['close'] / eth['close'].shift(1) - 1
eth['price_chg_4h'] = eth['close'] / eth['close'].shift(4) - 1
eth['price_chg_24h'] = eth['close'] / eth['close'].shift(24) - 1

# 48H内回撤
eth['high_48h'] = eth['high'].rolling(48, min_periods=1).max()
eth['drawdown_48h'] = eth['close'] / eth['high_48h'] - 1

# 20天高点
eth['high_20d'] = eth['high'].rolling(20*24, min_periods=1).max()

# 年份
eth['year'] = pd.to_datetime(eth['candle_begin_time']).dt.year

# =============================================================================
# 3. 定义信号
# =============================================================================
print("\n定义信号...")

# 研究9信号
eth['research9'] = (
    (eth['drawdown_48h'] <= -0.07) &           # 48H回撤>=7%
    (eth['price_chg_4h'] >= 0.015) &            # 4H动量>=1.5%
    (eth['ma20'] > eth['ma50']) &               # MA20>MA50
    (eth['close'] > eth['ma120']) &             # 价格>MA120
    (eth['close'] >= eth['high_20d'] * 0.85)   # 在20日高点85%以上
).astype(int)

# 本研究最优: MA100支撑+回撤+趋势
eth['support_ma100'] = (
    (eth['low'] <= eth['ma100'] * 1.01) &      # 触碰MA100
    (eth['close'] > eth['ma100']) &             # 收盘在MA100上
    (eth['close'] > eth['open']) &               # 阳线
    (eth['drawdown_48h'] <= -0.07) &            # 48H回撤>=7%
    (eth['ma20'] > eth['ma50'])                 # 趋势向上
).astype(int)

# 探索: 将支撑位概念加入研究9
eth['research9_plus_ma_support'] = (
    (eth['research9'] == 1) &
    ((eth['low'] <= eth['ma50'] * 1.02) |
     (eth['low'] <= eth['ma100'] * 1.02) |
     (eth['low'] <= eth['ma200'] * 1.02))
).astype(int)

# 探索: 放宽研究9的条件，用支撑位替代部分条件
eth['support_hybrid_v1'] = (
    (eth['low'] <= eth['ma100'] * 1.01) &      # 触碰MA100
    (eth['close'] > eth['ma100']) &             # 收盘在MA100上
    (eth['close'] > eth['open']) &               # 阳线
    (eth['drawdown_48h'] <= -0.07) &            # 48H回撤>=7%
    (eth['ma20'] > eth['ma50']) &               # 趋势向上
    (eth['price_chg_4h'] >= 0.01)               # 4H动量>=1% (放宽)
).astype(int)

eth['support_hybrid_v2'] = (
    (eth['low'] <= eth['ma100'] * 1.01) &      # 触碰MA100
    (eth['close'] > eth['ma100']) &             # 收盘在MA100上
    (eth['close'] > eth['open']) &               # 阳线
    (eth['drawdown_48h'] <= -0.05) &            # 48H回撤>=5% (放宽)
    (eth['ma20'] > eth['ma50']) &               # 趋势向上
    (eth['vol_ratio'] >= 1.5)                   # 放量确认
).astype(int)

# 探索: 使用MA200作为更强支撑
eth['support_ma200_dd'] = (
    (eth['low'] <= eth['ma200'] * 1.01) &      # 触碰MA200
    (eth['close'] > eth['ma200']) &             # 收盘在MA200上
    (eth['close'] > eth['open']) &               # 阳线
    (eth['drawdown_48h'] <= -0.07) &            # 48H回撤>=7%
    (eth['ma20'] > eth['ma50'])                 # 趋势向上
).astype(int)

# 探索: 触碰MA50/100/200任意一个
eth['support_any_ma'] = (
    ((eth['low'] <= eth['ma50'] * 1.01) |
     (eth['low'] <= eth['ma100'] * 1.01) |
     (eth['low'] <= eth['ma200'] * 1.01)) &
    (eth['close'] > eth['open']) &               # 阳线
    (eth['drawdown_48h'] <= -0.07) &            # 48H回撤>=7%
    (eth['ma20'] > eth['ma50']) &               # 趋势向上
    (eth['price_chg_4h'] >= 0.01)               # 有反弹动量
).astype(int)

# 探索: 更精确的支撑信号
eth['precise_support'] = (
    (eth['low'] <= eth['ma100'] * 1.005) &     # 更接近MA100
    (eth['close'] > eth['ma100'] * 1.005) &    # 收盘明显在MA100上方
    (eth['close'] > eth['open']) &               # 阳线
    ((eth['close'] - eth['low']) / eth['low'] >= 0.015) &  # 从低点反弹>=1.5%
    (eth['drawdown_48h'] <= -0.05) &            # 48H回撤>=5%
    (eth['ma20'] > eth['ma50']) &               # 趋势向上
    (eth['close'] > eth['ma120'])               # 处于上升趋势
).astype(int)

# =============================================================================
# 4. 统计函数
# =============================================================================
def calc_signal_stats(df, signal_col, holding_hours=[12, 24, 48, 72]):
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
                results[f'{h}h_std'] = returns.std() * 100
                results[f'{h}h_winrate'] = (returns > 0).mean() * 100
                results[f'{h}h_sharpe'] = returns.mean() / returns.std() * np.sqrt(365*24/h) if returns.std() > 0 else 0

    return results

def print_stats(name, stats):
    if stats is None:
        print(f"{name}: 无信号")
        return

    print(f"\n{'='*70}")
    print(f"【{name}】")
    print(f"信号次数: {stats['signal_count']}, 信号占比: {stats['signal_ratio']:.2f}%")
    print(f"{'持有':<6} {'平均收益':<10} {'胜率':<8} {'夏普':<8}")
    for h in [12, 24, 48, 72]:
        if f'{h}h_mean' in stats:
            print(f"{h}H      {stats[f'{h}h_mean']:>8.2f}%  {stats[f'{h}h_winrate']:>6.1f}%  {stats[f'{h}h_sharpe']:>7.2f}")

# =============================================================================
# 5. 信号分析
# =============================================================================
print("\n" + "="*80)
print("信号对比分析")
print("="*80)

signals_to_test = [
    ('research9', '研究9基准: 回调反弹'),
    ('support_ma100', '本研究: MA100支撑+回撤7%+趋势'),
    ('research9_plus_ma_support', '研究9 + 均线支撑过滤'),
    ('support_hybrid_v1', '混合V1: MA100支撑+回撤7%+4H动量1%'),
    ('support_hybrid_v2', '混合V2: MA100支撑+回撤5%+放量1.5x'),
    ('support_ma200_dd', 'MA200支撑+回撤7%+趋势'),
    ('support_any_ma', '任意均线支撑+回撤7%+趋势+动量'),
    ('precise_support', '精确MA100支撑+反弹1.5%+回撤5%'),
]

for col, name in signals_to_test:
    stats = calc_signal_stats(eth, col)
    print_stats(name, stats)

# =============================================================================
# 6. 信号重叠分析
# =============================================================================
print("\n" + "="*80)
print("信号重叠分析")
print("="*80)

r9_signals = eth[eth['research9'] == 1].index.tolist()
ma100_signals = eth[eth['support_ma100'] == 1].index.tolist()

print(f"\n研究9信号数: {len(r9_signals)}")
print(f"MA100支撑信号数: {len(ma100_signals)}")

overlap = set(r9_signals) & set(ma100_signals)
print(f"重叠信号数: {len(overlap)}")

only_r9 = set(r9_signals) - set(ma100_signals)
only_ma100 = set(ma100_signals) - set(r9_signals)
print(f"仅研究9: {len(only_r9)}")
print(f"仅MA100支撑: {len(only_ma100)}")

# 分析重叠部分的收益
if len(overlap) > 0:
    overlap_ret = eth.loc[list(overlap), 'future_48h'].dropna()
    print(f"\n重叠信号的48H收益: {overlap_ret.mean()*100:.2f}%, 胜率: {(overlap_ret>0).mean()*100:.1f}%")

if len(only_r9) > 0:
    only_r9_ret = eth.loc[list(only_r9), 'future_48h'].dropna()
    print(f"仅研究9信号的48H收益: {only_r9_ret.mean()*100:.2f}%, 胜率: {(only_r9_ret>0).mean()*100:.1f}%")

if len(only_ma100) > 0:
    only_ma100_ret = eth.loc[list(only_ma100), 'future_48h'].dropna()
    print(f"仅MA100支撑信号的48H收益: {only_ma100_ret.mean()*100:.2f}%, 胜率: {(only_ma100_ret>0).mean()*100:.1f}%")

# =============================================================================
# 7. 年度稳健性
# =============================================================================
print("\n" + "="*80)
print("年度稳健性检验")
print("="*80)

for sig_name, desc in [('research9', '研究9'), ('support_ma100', 'MA100支撑'), ('precise_support', '精确支撑')]:
    if eth[sig_name].sum() > 0:
        print(f"\n{desc} 年度检验:")
        print("-" * 50)
        for year in sorted(eth['year'].unique()):
            mask = (eth['year'] == year) & (eth[sig_name] == 1)
            ret = eth.loc[mask, 'future_48h'].dropna()
            if len(ret) >= 1:
                print(f"{year}年: 信号数={len(ret):<4}, 48H收益={ret.mean()*100:>6.2f}%, 胜率={(ret>0).mean()*100:.1f}%")

# =============================================================================
# 8. 支撑位有效性深入分析
# =============================================================================
print("\n" + "="*80)
print("支撑位有效性深入分析")
print("="*80)

# 分析不同均线作为支撑的有效性
print("\n--- 回撤>=7%时，触碰不同均线的效果 ---")

for ma in [20, 50, 100, 200]:
    # 回撤>=7%且触碰均线
    cond = (
        (eth['low'] <= eth[f'ma{ma}'] * 1.01) &
        (eth['close'] > eth[f'ma{ma}']) &
        (eth['close'] > eth['open']) &
        (eth['drawdown_48h'] <= -0.07)
    )
    count = cond.sum()
    if count > 0:
        ret = eth.loc[cond, 'future_48h'].dropna()
        print(f"MA{ma}支撑+回撤7%: N={count:<4}, 48H收益={ret.mean()*100:>6.2f}%, 胜率={(ret>0).mean()*100:.1f}%")

print("\n--- 加入趋势过滤后 ---")

for ma in [50, 100, 200]:
    # 加入趋势过滤
    cond = (
        (eth['low'] <= eth[f'ma{ma}'] * 1.01) &
        (eth['close'] > eth[f'ma{ma}']) &
        (eth['close'] > eth['open']) &
        (eth['drawdown_48h'] <= -0.07) &
        (eth['ma20'] > eth['ma50'])
    )
    count = cond.sum()
    if count > 0:
        ret = eth.loc[cond, 'future_48h'].dropna()
        print(f"MA{ma}支撑+回撤7%+趋势: N={count:<4}, 48H收益={ret.mean()*100:>6.2f}%, 胜率={(ret>0).mean()*100:.1f}%")

print("\n--- 不同回撤深度的效果 (MA100支撑+趋势) ---")

for dd in [0.03, 0.05, 0.07, 0.10, 0.15]:
    cond = (
        (eth['low'] <= eth['ma100'] * 1.01) &
        (eth['close'] > eth['ma100']) &
        (eth['close'] > eth['open']) &
        (eth['drawdown_48h'] <= -dd) &
        (eth['ma20'] > eth['ma50'])
    )
    count = cond.sum()
    if count > 0:
        ret = eth.loc[cond, 'future_48h'].dropna()
        print(f"回撤>={dd*100:.0f}%: N={count:<4}, 48H收益={ret.mean()*100:>6.2f}%, 胜率={(ret>0).mean()*100:.1f}%")

# =============================================================================
# 9. 组合信号探索
# =============================================================================
print("\n" + "="*80)
print("组合信号探索")
print("="*80)

# 研究9的核心条件 + 支撑位概念
print("\n--- 研究9条件分解 + 支撑位 ---")

# 研究9的核心是: 回撤+动量反弹+趋势+高位过滤
# 支撑位可以替代/增强"回撤"条件

# 1. 支撑位替代回撤条件
eth['support_based_v1'] = (
    (eth['low'] <= eth['ma100'] * 1.01) &      # 支撑位
    (eth['price_chg_4h'] >= 0.015) &            # 4H动量反弹
    (eth['ma20'] > eth['ma50']) &               # 趋势
    (eth['close'] > eth['ma120']) &             # 上升趋势
    (eth['close'] >= eth['high_20d'] * 0.85)   # 高位过滤
).astype(int)

stats = calc_signal_stats(eth, 'support_based_v1')
print_stats("支撑位替代回撤(MA100支撑+4H动量1.5%+趋势+高位)", stats)

# 2. 支撑位 + 回撤条件
eth['support_based_v2'] = (
    (eth['low'] <= eth['ma100'] * 1.01) &      # 支撑位
    (eth['drawdown_48h'] <= -0.05) &            # 回撤>=5%
    (eth['price_chg_4h'] >= 0.01) &             # 4H动量>=1%
    (eth['ma20'] > eth['ma50']) &               # 趋势
    (eth['close'] > eth['ma120'])               # 上升趋势
).astype(int)

stats = calc_signal_stats(eth, 'support_based_v2')
print_stats("支撑位+回撤5%(MA100支撑+回撤5%+动量1%)", stats)

# 3. 双均线支撑
eth['double_ma_support'] = (
    ((eth['low'] <= eth['ma50'] * 1.01) & (eth['low'] <= eth['ma100'] * 1.02)) &  # 同时接近MA50和MA100
    (eth['close'] > eth['ma50']) &
    (eth['close'] > eth['open']) &
    (eth['drawdown_48h'] <= -0.05) &
    (eth['ma20'] > eth['ma50'])
).astype(int)

stats = calc_signal_stats(eth, 'double_ma_support')
print_stats("双均线支撑(MA50+MA100同时)", stats)

# 4. 支撑位 + 放量
eth['support_volume'] = (
    (eth['low'] <= eth['ma100'] * 1.01) &
    (eth['close'] > eth['ma100']) &
    (eth['close'] > eth['open']) &
    (eth['vol_ratio'] >= 2.0) &                 # 放量2x
    (eth['drawdown_48h'] <= -0.05) &
    (eth['ma20'] > eth['ma50'])
).astype(int)

stats = calc_signal_stats(eth, 'support_volume')
print_stats("支撑位+放量2x(MA100支撑+回撤5%+放量)", stats)

# =============================================================================
# 10. 总结
# =============================================================================
print("\n" + "="*80)
print("研究总结")
print("="*80)

print("""
核心发现:

1. 支撑位信号单独使用效果有限
   - 单纯触碰均线获得支撑的信号，48H收益在0.3%-0.7%左右
   - 远不及研究9的7.77%

2. 前期低点支撑完全失效
   - 回踩前低(20日/50日)的信号收益为负
   - 说明"回踩前低"不是有效的支撑判断方式

3. 多次测试同一支撑位也无效
   - 测试次数越多，收益反而越差
   - 说明多次测试可能意味着支撑即将失效

4. 支撑位 + 回撤条件组合有一定效果
   - MA100支撑+48H回撤>=7%+趋势: 3.32%收益，72.5%胜率
   - 但仍不及研究9的7.77%

5. 关键洞察: 研究9的成功不在于"支撑位"
   - 研究9的核心是"趋势中回调+反弹确认+高位过滤"
   - 4H动量反弹(>=1.5%)是关键的入场确认
   - 20日高点85%以上的高位过滤大幅提升胜率

建议:
- 支撑位概念可作为辅助过滤，但不应作为核心信号
- 研究9的框架更有效，应继续在该框架上优化
- 本研究未能超越研究9，但验证了支撑位概念的局限性
""")

print("\n研究完成!")
