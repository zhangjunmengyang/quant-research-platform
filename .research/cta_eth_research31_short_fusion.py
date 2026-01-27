"""
CTA-ETH-研究31: 做空信号投票融合研究

研究四个核心做空信号的融合机制:
- 研究25: 强熊市+假突破+24H涨>10%+强量缩 (72H胜率100%, 7信号)
- 研究27: 熊市天量下跌 (72H胜率82.6%, 23信号)
- 研究29: 熊市反弹衰竭 (12H胜率87.5%, 16信号)
- 研究30: 日周共振+反弹+RSI (24H胜率83.3%, 12信号)
"""

import pickle
import pandas as pd
import numpy as np
from datetime import datetime

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
print(f"列: {list(eth.columns)[:20]}...")

# ========================================
# 2. 基础指标计算
# ========================================

# 均线
eth['MA50'] = eth['close'].rolling(50).mean()
eth['MA120'] = eth['close'].rolling(120).mean()
eth['MA200'] = eth['close'].rolling(200).mean()

# 日线均线
eth['MA20_daily'] = eth['close'].rolling(20*24).mean()  # 约20日均线
eth['MA50_daily'] = eth['close'].rolling(50*24).mean()  # 约50日均线

# 周线均线
eth['MA5_weekly'] = eth['close'].rolling(5*24*7).mean()  # 约5周均线
eth['MA10_weekly'] = eth['close'].rolling(10*24*7).mean()  # 约10周均线

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
eth['ret_8h'] = eth['close'].pct_change(8) * 100
eth['ret_10h'] = eth['close'].pct_change(10) * 100
eth['ret_12h'] = eth['close'].pct_change(12) * 100
eth['ret_24h'] = eth['close'].pct_change(24) * 100
eth['ret_48h'] = eth['close'].pct_change(48) * 100

# 未来收益 (做空收益用负值表示)
eth['fwd_ret_12h'] = -eth['close'].pct_change(-12) * 100
eth['fwd_ret_24h'] = -eth['close'].pct_change(-24) * 100
eth['fwd_ret_48h'] = -eth['close'].pct_change(-48) * 100
eth['fwd_ret_72h'] = -eth['close'].pct_change(-72) * 100

# 区间最高/最低
eth['high_8h'] = eth['high'].rolling(8).max()
eth['high_24h'] = eth['high'].rolling(24).max()
eth['low_8h'] = eth['low'].rolling(8).min()

# ========================================
# 3. 定义四个核心做空信号
# ========================================

def signal_25_strong_bear_breakout(df):
    """
    研究25: 强熊市+假突破+24H涨>10%+强量缩
    条件:
    - 强熊市: MA50 < MA120 * 0.95
    - 假突破: 价格曾突破MA50但收盘回落
    - 24H涨幅 > 10%
    - 成交量 < 0.8 * vol_ma10 (强量缩)
    """
    # 强熊市
    strong_bear = df['MA50'] < df['MA120'] * 0.95

    # 24H涨幅 > 10%
    rally_24h = df['ret_24h'] > 10

    # 成交量缩量 < 0.8倍均量
    vol_shrink = df['volume'] < 0.8 * df['vol_ma10']

    # 假突破: 区间最高曾突破MA50但收盘低于MA50
    # 使用8H区间判断假突破
    fake_breakout = (df['high_8h'] > df['MA50']) & (df['close'] < df['MA50'])

    signal = strong_bear & rally_24h & vol_shrink & fake_breakout
    return signal


def signal_27_bear_volume_drop(df):
    """
    研究27: 熊市天量下跌
    条件:
    - 强熊市: MA50 < MA200
    - 放量 > 4倍均量
    - 当前1H跌幅在 2.5% - 4% (适度下跌)
    - 24H累计跌幅 > 5%
    """
    # 强熊市
    bear_market = df['MA50'] < df['MA200']

    # 放量 > 4倍
    high_volume = df['volume'] > 4 * df['vol_ma20']

    # 1H跌幅在2.5%-4%区间
    ret_1h = df['close'].pct_change(1) * 100
    moderate_drop = (ret_1h < -2.5) & (ret_1h > -4)

    # 24H累计跌幅 > 5%
    cum_drop_24h = df['ret_24h'] < -5

    signal = bear_market & high_volume & moderate_drop & cum_drop_24h
    return signal


def signal_29_bear_rally_exhaustion(df):
    """
    研究29: 熊市反弹衰竭
    条件:
    - 熊市: MA50 < MA200
    - 12H内反弹 > 8%
    - 过去12H内有 > 2%的回落
    """
    # 熊市
    bear_market = df['MA50'] < df['MA200']

    # 12H反弹 > 8%
    rally_12h = df['ret_12h'] > 8

    # 计算12H内的回落: 从最高点到当前的回落
    rolling_high_12h = df['high'].rolling(12).max()
    pullback_from_high = (rolling_high_12h - df['close']) / rolling_high_12h * 100
    has_pullback = pullback_from_high > 2

    signal = bear_market & rally_12h & has_pullback
    return signal


def signal_30_multi_timeframe_short(df):
    """
    研究30: 日周共振+反弹+RSI
    条件:
    - 日线空头: MA20_daily < MA50_daily
    - 周线空头: MA5_weekly < MA10_weekly
    - 24H涨幅 > 8%
    - RSI > 70
    """
    # 日线空头排列
    daily_bear = df['MA20_daily'] < df['MA50_daily']

    # 周线空头排列
    weekly_bear = df['MA5_weekly'] < df['MA10_weekly']

    # 24H反弹 > 8%
    rally_24h = df['ret_24h'] > 8

    # RSI超买
    rsi_overbought = df['RSI'] > 70

    signal = daily_bear & weekly_bear & rally_24h & rsi_overbought
    return signal


# ========================================
# 4. 生成信号并去重
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


# 计算各信号
eth['sig_25'] = signal_25_strong_bear_breakout(eth)
eth['sig_27'] = signal_27_bear_volume_drop(eth)
eth['sig_29'] = signal_29_bear_rally_exhaustion(eth)
eth['sig_30'] = signal_30_multi_timeframe_short(eth)

# 去重 (使用24H间隔)
eth['sig_25_clean'] = remove_overlap_signals(eth['sig_25'], 24)
eth['sig_27_clean'] = remove_overlap_signals(eth['sig_27'], 24)
eth['sig_29_clean'] = remove_overlap_signals(eth['sig_29'], 12)  # 研究29用12H
eth['sig_30_clean'] = remove_overlap_signals(eth['sig_30'], 24)

# 统计
print("\n" + "="*60)
print("各信号统计 (去重后):")
print("="*60)
for sig_name in ['sig_25_clean', 'sig_27_clean', 'sig_29_clean', 'sig_30_clean']:
    count = eth[sig_name].sum()
    print(f"{sig_name}: {count}个信号")

# ========================================
# 5. 分析信号绩效
# ========================================

def analyze_signal_performance(df, signal_col, periods=[12, 24, 48, 72]):
    """分析信号在不同持有期的表现"""
    signals = df[df[signal_col]]
    if len(signals) == 0:
        return None

    results = {'signal_count': len(signals)}
    for period in periods:
        fwd_col = f'fwd_ret_{period}h'
        if fwd_col in df.columns:
            returns = signals[fwd_col].dropna()
            results[f'{period}h_mean'] = returns.mean()
            results[f'{period}h_win_rate'] = (returns > 0).mean() * 100
            results[f'{period}h_max'] = returns.max()
            results[f'{period}h_min'] = returns.min()

    return results


print("\n" + "="*60)
print("各信号绩效分析:")
print("="*60)

for sig_name, orig_name in [('sig_25_clean', '研究25'), ('sig_27_clean', '研究27'),
                             ('sig_29_clean', '研究29'), ('sig_30_clean', '研究30')]:
    perf = analyze_signal_performance(eth, sig_name)
    if perf:
        print(f"\n{orig_name} ({sig_name}):")
        print(f"  信号数: {perf['signal_count']}")
        for period in [12, 24, 48, 72]:
            if f'{period}h_mean' in perf:
                print(f"  {period}H: 收益{perf[f'{period}h_mean']:.2f}%, 胜率{perf[f'{period}h_win_rate']:.1f}%")


# ========================================
# 6. 信号重叠分析
# ========================================

print("\n" + "="*60)
print("信号重叠分析:")
print("="*60)

# 计算信号投票数
eth['vote_count'] = (eth['sig_25_clean'].astype(int) +
                    eth['sig_27_clean'].astype(int) +
                    eth['sig_29_clean'].astype(int) +
                    eth['sig_30_clean'].astype(int))

print("\n投票分布:")
print(eth['vote_count'].value_counts().sort_index())

# 分析不同投票数的重叠情况
print("\n信号重叠明细:")
signals_df = eth[eth['vote_count'] >= 1][['sig_25_clean', 'sig_27_clean', 'sig_29_clean', 'sig_30_clean', 'vote_count']]

# 统计两两重叠
overlap_matrix = pd.DataFrame(index=['研究25', '研究27', '研究29', '研究30'],
                              columns=['研究25', '研究27', '研究29', '研究30'])

sig_cols = ['sig_25_clean', 'sig_27_clean', 'sig_29_clean', 'sig_30_clean']
sig_names = ['研究25', '研究27', '研究29', '研究30']

for i, (col_i, name_i) in enumerate(zip(sig_cols, sig_names)):
    for j, (col_j, name_j) in enumerate(zip(sig_cols, sig_names)):
        if i == j:
            overlap_matrix.loc[name_i, name_j] = eth[col_i].sum()
        else:
            overlap = (eth[col_i] & eth[col_j]).sum()
            overlap_matrix.loc[name_i, name_j] = overlap

print("\n信号重叠矩阵 (对角线为各信号总数):")
print(overlap_matrix)

# ========================================
# 7. 投票机制测试
# ========================================

print("\n" + "="*60)
print("投票机制测试:")
print("="*60)

# 测试不同投票阈值
for threshold in [1, 2, 3, 4]:
    vote_signal = eth['vote_count'] >= threshold
    vote_signal_clean = remove_overlap_signals(vote_signal, 24)

    signals = eth[vote_signal_clean]
    if len(signals) > 0:
        print(f"\n投票阈值 >= {threshold} ({len(signals)}个信号):")
        for period in [12, 24, 48, 72]:
            fwd_col = f'fwd_ret_{period}h'
            returns = signals[fwd_col].dropna()
            if len(returns) > 0:
                win_rate = (returns > 0).mean() * 100
                mean_ret = returns.mean()
                print(f"  {period}H: 收益{mean_ret:.2f}%, 胜率{win_rate:.1f}% (n={len(returns)})")


# ========================================
# 8. 信号组合优化
# ========================================

print("\n" + "="*60)
print("信号组合优化:")
print("="*60)

# 测试不同信号组合
from itertools import combinations

combo_results = []

for r in range(1, 5):  # 1到4个信号的组合
    for combo in combinations(range(4), r):
        combo_names = [sig_names[i] for i in combo]
        combo_cols = [sig_cols[i] for i in combo]

        # 计算组合信号 (任一触发)
        any_signal = eth[combo_cols].any(axis=1)
        any_signal_clean = remove_overlap_signals(any_signal, 24)

        signals = eth[any_signal_clean]
        if len(signals) >= 3:  # 至少3个信号
            for period in [24, 48, 72]:
                fwd_col = f'fwd_ret_{period}h'
                returns = signals[fwd_col].dropna()
                if len(returns) >= 3:
                    win_rate = (returns > 0).mean() * 100
                    mean_ret = returns.mean()
                    combo_results.append({
                        'combo': '+'.join(combo_names),
                        'n_signals': len(combo_names),
                        'signal_count': len(signals),
                        'period': f'{period}H',
                        'win_rate': win_rate,
                        'mean_ret': mean_ret,
                        'sharpe': mean_ret / returns.std() if returns.std() > 0 else 0
                    })

combo_df = pd.DataFrame(combo_results)
if len(combo_df) > 0:
    # 按夏普排序
    combo_df_sorted = combo_df.sort_values('sharpe', ascending=False)
    print("\n组合绩效排名 (按夏普比率):")
    print(combo_df_sorted.head(20).to_string(index=False))


# ========================================
# 9. 主辅信号关系分析
# ========================================

print("\n" + "="*60)
print("主辅信号关系分析:")
print("="*60)

# 分析各信号单独表现
print("\n各信号独立表现 (72H):")
signal_perf_72h = []
for sig_name, orig_name in [('sig_25_clean', '研究25'), ('sig_27_clean', '研究27'),
                             ('sig_29_clean', '研究29'), ('sig_30_clean', '研究30')]:
    signals = eth[eth[sig_name]]
    if len(signals) > 0:
        returns = signals['fwd_ret_72h'].dropna()
        if len(returns) > 0:
            signal_perf_72h.append({
                'signal': orig_name,
                'count': len(returns),
                'win_rate': (returns > 0).mean() * 100,
                'mean_ret': returns.mean(),
                'max_ret': returns.max(),
                'min_ret': returns.min()
            })

perf_df = pd.DataFrame(signal_perf_72h)
print(perf_df.to_string(index=False))

# 分析信号增强效果
print("\n信号增强效果 (当多个信号同时触发时):")
for sig_name, orig_name in [('sig_25_clean', '研究25'), ('sig_27_clean', '研究27'),
                             ('sig_29_clean', '研究29'), ('sig_30_clean', '研究30')]:
    base_signals = eth[eth[sig_name]]
    if len(base_signals) > 0:
        # 单独触发
        single = base_signals[base_signals['vote_count'] == 1]
        # 多信号共振
        multi = base_signals[base_signals['vote_count'] >= 2]

        if len(single) > 0 and len(multi) > 0:
            single_ret = single['fwd_ret_72h'].dropna().mean()
            multi_ret = multi['fwd_ret_72h'].dropna().mean()
            print(f"{orig_name}: 单独{single_ret:.2f}% (n={len(single)}) vs 共振{multi_ret:.2f}% (n={len(multi)})")


# ========================================
# 10. 最优融合策略
# ========================================

print("\n" + "="*60)
print("最优融合策略设计:")
print("="*60)

# 策略1: 研究25为主信号 (胜率最高)
print("\n策略1: 研究25为主，其他为辅")
sig25_signals = eth[eth['sig_25_clean']]
if len(sig25_signals) > 0:
    for period in [24, 48, 72]:
        returns = sig25_signals[f'fwd_ret_{period}h'].dropna()
        if len(returns) > 0:
            print(f"  {period}H: 收益{returns.mean():.2f}%, 胜率{(returns>0).mean()*100:.1f}%")

# 策略2: 投票阈值>=2
print("\n策略2: 投票阈值>=2")
vote2_signal = remove_overlap_signals(eth['vote_count'] >= 2, 24)
vote2_signals = eth[vote2_signal]
if len(vote2_signals) > 0:
    for period in [24, 48, 72]:
        returns = vote2_signals[f'fwd_ret_{period}h'].dropna()
        if len(returns) > 0:
            print(f"  {period}H: 收益{returns.mean():.2f}%, 胜率{(returns>0).mean()*100:.1f}% (n={len(returns)})")

# 策略3: 加权投票 (胜率加权)
print("\n策略3: 加权投票 (按原研究胜率加权)")
# 权重: 研究25=100%, 研究29=87.5%, 研究30=83.3%, 研究27=82.6%
eth['weighted_vote'] = (eth['sig_25_clean'].astype(float) * 1.0 +
                        eth['sig_29_clean'].astype(float) * 0.875 +
                        eth['sig_30_clean'].astype(float) * 0.833 +
                        eth['sig_27_clean'].astype(float) * 0.826)

for threshold in [0.5, 1.0, 1.5, 2.0]:
    weighted_signal = remove_overlap_signals(eth['weighted_vote'] >= threshold, 24)
    signals = eth[weighted_signal]
    if len(signals) >= 3:
        print(f"\n  加权阈值 >= {threshold} ({len(signals)}个信号):")
        for period in [24, 48, 72]:
            returns = signals[f'fwd_ret_{period}h'].dropna()
            if len(returns) >= 3:
                print(f"    {period}H: 收益{returns.mean():.2f}%, 胜率{(returns>0).mean()*100:.1f}%")

# 策略4: 研究25 + 熊市确认
print("\n策略4: 研究25 + 任一其他信号确认")
sig25_plus = eth['sig_25_clean'] & (eth['sig_27_clean'] | eth['sig_29_clean'] | eth['sig_30_clean'])
sig25_plus_clean = remove_overlap_signals(sig25_plus, 24)
signals = eth[sig25_plus_clean]
if len(signals) > 0:
    for period in [24, 48, 72]:
        returns = signals[f'fwd_ret_{period}h'].dropna()
        if len(returns) > 0:
            print(f"  {period}H: 收益{returns.mean():.2f}%, 胜率{(returns>0).mean()*100:.1f}% (n={len(returns)})")


# ========================================
# 11. 输出信号时间序列
# ========================================

print("\n" + "="*60)
print("信号时间明细:")
print("="*60)

# 显示所有信号触发时间
signal_times = eth[eth['vote_count'] >= 1][['close', 'ret_24h', 'RSI', 'vote_count',
                                             'sig_25_clean', 'sig_27_clean', 'sig_29_clean', 'sig_30_clean',
                                             'fwd_ret_24h', 'fwd_ret_48h', 'fwd_ret_72h']]
print(f"\n共{len(signal_times)}个信号时点 (至少1个信号触发):")
print(signal_times.to_string())


# ========================================
# 12. 年度分布分析
# ========================================

print("\n" + "="*60)
print("年度分布分析:")
print("="*60)

eth['year'] = eth.index.year
for sig_col, sig_name in [('sig_25_clean', '研究25'), ('sig_27_clean', '研究27'),
                          ('sig_29_clean', '研究29'), ('sig_30_clean', '研究30')]:
    yearly = eth[eth[sig_col]].groupby('year').size()
    print(f"\n{sig_name}年度分布:")
    print(yearly.to_string())

# 融合信号年度分布
print("\n投票>=2信号年度分布:")
vote2_yearly = eth[eth['vote_count'] >= 2].groupby('year').size()
print(vote2_yearly.to_string())

print("\n" + "="*60)
print("研究31完成")
print("="*60)
