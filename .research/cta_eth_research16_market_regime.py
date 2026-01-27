# -*- coding: utf-8 -*-
"""
【CTA-ETH-研究16】市场状态识别与策略适应性研究

研究目标:
1. 市场状态识别方法(牛市/熊市/震荡)
2. 各状态下策略表现分析
3. 策略切换机制探索
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

print("="*80)
print("【CTA-ETH-研究16】市场状态识别与策略适应性研究")
print("="*80)

print("\n加载数据...")
with open(data_path, 'rb') as f:
    swap_dict = pickle.load(f)

eth = swap_dict['ETH-USDT'].copy()
eth = eth.dropna(subset=['close'])
eth = eth.reset_index(drop=True)

print(f"ETH有效数据: {len(eth)} 行")
print(f"时间范围: {eth['candle_begin_time'].min()} ~ {eth['candle_begin_time'].max()}")

# =============================================================================
# 2. 计算基础指标
# =============================================================================
print("\n计算基础指标...")

# 未来收益
for h in [12, 24, 48, 72]:
    eth[f'future_{h}h'] = eth['close'].shift(-h) / eth['close'] - 1

# 均线系统
for ma in [20, 50, 100, 120, 200]:
    eth[f'ma{ma}'] = eth['close'].rolling(ma, min_periods=1).mean()

# 日线级别均线 (24根K线为1天)
eth['ma50d'] = eth['close'].rolling(50*24, min_periods=1).mean()
eth['ma200d'] = eth['close'].rolling(200*24, min_periods=1).mean()

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

# ATR (Average True Range)
eth['tr'] = np.maximum(
    eth['high'] - eth['low'],
    np.maximum(
        abs(eth['high'] - eth['close'].shift(1)),
        abs(eth['low'] - eth['close'].shift(1))
    )
)
eth['atr14'] = eth['tr'].rolling(14).mean()
eth['atr_ratio'] = eth['atr14'] / eth['close']

# ADX计算
def calc_adx(df, period=14):
    # 计算+DM和-DM
    df['plus_dm'] = np.where(
        (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
        np.maximum(df['high'] - df['high'].shift(1), 0),
        0
    )
    df['minus_dm'] = np.where(
        (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
        np.maximum(df['low'].shift(1) - df['low'], 0),
        0
    )

    # 平滑
    df['plus_dm_smooth'] = df['plus_dm'].rolling(period).mean()
    df['minus_dm_smooth'] = df['minus_dm'].rolling(period).mean()
    df['tr_smooth'] = df['tr'].rolling(period).mean()

    # +DI和-DI
    df['plus_di'] = 100 * df['plus_dm_smooth'] / df['tr_smooth']
    df['minus_di'] = 100 * df['minus_dm_smooth'] / df['tr_smooth']

    # DX和ADX
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = df['dx'].rolling(period).mean()

    return df

eth = calc_adx(eth, 14)

# 过去N天收益率
eth['return_30d'] = eth['close'] / eth['close'].shift(30*24) - 1
eth['return_60d'] = eth['close'] / eth['close'].shift(60*24) - 1
eth['return_200d'] = eth['close'] / eth['close'].shift(200*24) - 1

# 波动率 (20日年化)
eth['volatility_20d'] = eth['price_chg_1h'].rolling(20*24).std() * np.sqrt(365*24) * 100

# 年份
eth['year'] = pd.to_datetime(eth['candle_begin_time']).dt.year
eth['month'] = pd.to_datetime(eth['candle_begin_time']).dt.month

print("指标计算完成")

# =============================================================================
# 3. 市场状态定义
# =============================================================================
print("\n" + "="*80)
print("市场状态识别方法")
print("="*80)

# 方法1: 均线位置 (MA50 vs MA200)
eth['regime_ma'] = np.where(
    eth['ma50d'] > eth['ma200d'] * 1.05,  # MA50显著高于MA200
    'bull',
    np.where(
        eth['ma50d'] < eth['ma200d'] * 0.95,  # MA50显著低于MA200
        'bear',
        'neutral'
    )
)

# 方法2: 200日收益率
eth['regime_return'] = np.where(
    eth['return_200d'] > 0.3,  # 200日涨幅>30%
    'bull',
    np.where(
        eth['return_200d'] < -0.3,  # 200日跌幅>30%
        'bear',
        'neutral'
    )
)

# 方法3: ADX趋势强度 + DI方向
eth['regime_adx'] = np.where(
    (eth['adx'] > 25) & (eth['plus_di'] > eth['minus_di']),  # 强趋势+上涨
    'bull',
    np.where(
        (eth['adx'] > 25) & (eth['minus_di'] > eth['plus_di']),  # 强趋势+下跌
        'bear',
        'range'  # 震荡
    )
)

# 方法4: 价格相对位置 (相对200日均线)
eth['regime_price'] = np.where(
    eth['close'] > eth['ma200d'] * 1.2,  # 价格高于MA200 20%
    'bull',
    np.where(
        eth['close'] < eth['ma200d'] * 0.8,  # 价格低于MA200 20%
        'bear',
        'neutral'
    )
)

# 方法5: 综合判断 (需要多数指标一致)
def get_consensus_regime(row):
    votes = []
    if pd.notna(row['regime_ma']):
        votes.append(row['regime_ma'])
    if pd.notna(row['regime_return']):
        votes.append(row['regime_return'])
    if pd.notna(row['regime_price']):
        votes.append(row['regime_price'])

    if len(votes) == 0:
        return 'unknown'

    bull_count = sum(1 for v in votes if v == 'bull')
    bear_count = sum(1 for v in votes if v == 'bear')

    if bull_count >= 2:
        return 'bull'
    elif bear_count >= 2:
        return 'bear'
    else:
        return 'neutral'

eth['regime_consensus'] = eth.apply(get_consensus_regime, axis=1)

# 打印各识别方法的分布
print("\n--- 各识别方法的市场状态分布 ---")
for method in ['regime_ma', 'regime_return', 'regime_adx', 'regime_price', 'regime_consensus']:
    valid_data = eth[eth[method].notna()]
    counts = valid_data[method].value_counts()
    total = len(valid_data)
    print(f"\n{method}:")
    for state, count in counts.items():
        print(f"  {state}: {count} ({count/total*100:.1f}%)")

# =============================================================================
# 4. 定义已验证的做多策略
# =============================================================================
print("\n" + "="*80)
print("定义已验证的做多策略")
print("="*80)

# 研究9: 趋势回调反弹 (目前最优)
eth['signal_r9'] = (
    (eth['drawdown_48h'] <= -0.07) &           # 48H回撤>=7%
    (eth['price_chg_4h'] >= 0.015) &            # 4H动量>=1.5%
    (eth['ma20'] > eth['ma50']) &               # MA20>MA50
    (eth['close'] > eth['ma120']) &             # 价格>MA120
    (eth['close'] >= eth['high_20d'] * 0.85)   # 在20日高点85%以上
).astype(int)

# 研究8: 突破50日+放量
eth['high_50d'] = eth['high'].rolling(50*24, min_periods=1).max()
eth['signal_r8'] = (
    (eth['close'] >= eth['high_50d'] * 0.995) &  # 接近或突破50日高点
    (eth['close'] > eth['open']) &                # 阳线
    (eth['vol_ratio'] >= 3.5) &                   # 放量3.5x
    (eth['price_chg_24h'] >= 0.02)               # 24H涨幅>2%
).astype(int)

# 研究6/7: 放量上涨+EMA
eth['ema12'] = eth['close'].ewm(span=12, adjust=False).mean()
eth['ema26'] = eth['close'].ewm(span=26, adjust=False).mean()
eth['signal_r6'] = (
    (eth['vol_ratio'] >= 3.5) &                  # 放量3.5x
    (eth['price_chg_1h'] >= 0.02) &              # 涨幅>2%
    (eth['ema12'] > eth['ema26'])                # EMA12>EMA26
).astype(int)

# 研究10: 波动率收缩+回调反弹
eth['bbw'] = (eth['close'].rolling(20).std() * 2) / eth['close'].rolling(20).mean()
eth['bbw_pct'] = eth['bbw'].rolling(100*24).rank(pct=True)
eth['ema50'] = eth['close'].ewm(span=50, adjust=False).mean()
eth['drawdown_24h'] = eth['close'] / eth['high'].rolling(24).max() - 1

eth['signal_r10'] = (
    (eth['bbw_pct'] <= 0.2) &                    # 带宽处于20%分位
    (eth['drawdown_24h'] <= -0.05) &             # 24H回调>5%
    (eth['price_chg_4h'] >= 0.01) &              # 4H反弹>1%
    (eth['close'] > eth['ema50'])                # 价格>EMA50
).astype(int)

# 研究12: 深回调+MFI支撑
# 简化版MFI
eth['typical_price'] = (eth['high'] + eth['low'] + eth['close']) / 3
eth['raw_money_flow'] = eth['typical_price'] * eth['volume']
eth['positive_flow'] = np.where(eth['typical_price'] > eth['typical_price'].shift(1), eth['raw_money_flow'], 0)
eth['negative_flow'] = np.where(eth['typical_price'] < eth['typical_price'].shift(1), eth['raw_money_flow'], 0)
eth['positive_flow_sum'] = eth['positive_flow'].rolling(14).sum()
eth['negative_flow_sum'] = eth['negative_flow'].rolling(14).sum()
eth['mfi'] = 100 - (100 / (1 + eth['positive_flow_sum'] / (eth['negative_flow_sum'] + 1e-10)))

eth['drawdown_5_10pct'] = (eth['drawdown_48h'] <= -0.05) & (eth['drawdown_48h'] >= -0.10)
eth['signal_r12'] = (
    (eth['ma20'] > eth['ma50']) &                # 上升趋势
    eth['drawdown_5_10pct'] &                    # 深回调5-10%
    (eth['mfi'] >= 65)                           # MFI>65
).astype(int)

# 简单基准: 任意时刻做多
eth['signal_baseline'] = 1

signals = {
    'signal_baseline': '任意时刻做多(基准)',
    'signal_r6': '研究6: 放量上涨+EMA',
    'signal_r8': '研究8: 突破50日+放量',
    'signal_r9': '研究9: 趋势回调反弹',
    'signal_r10': '研究10: 波动率收缩+回调',
    'signal_r12': '研究12: 深回调+MFI支撑'
}

print(f"已定义 {len(signals)} 个策略")

# =============================================================================
# 5. 各市场状态下的策略表现
# =============================================================================
print("\n" + "="*80)
print("各市场状态下的策略表现分析")
print("="*80)

def analyze_signal_by_regime(df, signal_col, regime_col='regime_consensus'):
    """分析信号在不同市场状态下的表现"""
    results = []

    for regime in ['bull', 'neutral', 'bear']:
        mask = (df[regime_col] == regime) & (df[signal_col] == 1)
        signal_df = df[mask]

        if len(signal_df) == 0:
            continue

        ret_48h = signal_df['future_48h'].dropna()
        if len(ret_48h) == 0:
            continue

        results.append({
            'regime': regime,
            'signal_count': len(signal_df),
            'mean_return': ret_48h.mean() * 100,
            'win_rate': (ret_48h > 0).mean() * 100,
            'std': ret_48h.std() * 100,
            'sharpe': ret_48h.mean() / ret_48h.std() * np.sqrt(365*24/48) if ret_48h.std() > 0 else 0
        })

    return pd.DataFrame(results)

# 使用综合判断方法
print("\n使用 regime_consensus (综合判断) 分析:")
print("-" * 80)

for sig_col, sig_name in signals.items():
    result = analyze_signal_by_regime(eth, sig_col, 'regime_consensus')
    if len(result) > 0:
        print(f"\n【{sig_name}】")
        for _, row in result.iterrows():
            print(f"  {row['regime']:8s}: N={row['signal_count']:<4}, 48H收益={row['mean_return']:>6.2f}%, 胜率={row['win_rate']:.1f}%, 夏普={row['sharpe']:.2f}")

# =============================================================================
# 6. 详细年度+市场状态分析
# =============================================================================
print("\n" + "="*80)
print("年度+市场状态详细分析")
print("="*80)

# 首先看各年份的市场状态分布
print("\n--- 各年份市场状态分布 ---")
regime_year = eth.groupby(['year', 'regime_consensus']).size().unstack(fill_value=0)
print(regime_year)

# 各年份+状态下的基准收益
print("\n--- 各年份各状态下的基准48H收益 ---")
for year in sorted(eth['year'].unique()):
    for regime in ['bull', 'neutral', 'bear']:
        mask = (eth['year'] == year) & (eth['regime_consensus'] == regime)
        if mask.sum() > 100:  # 至少有100个样本
            ret = eth.loc[mask, 'future_48h'].dropna()
            print(f"{year}年 {regime:8s}: N={len(ret):<5}, 基准48H={ret.mean()*100:>6.2f}%, 胜率={(ret>0).mean()*100:.1f}%")

# =============================================================================
# 7. 策略在熊市的表现
# =============================================================================
print("\n" + "="*80)
print("重点: 策略在熊市的表现")
print("="*80)

print("\n熊市期间各策略表现:")
print("-" * 80)

bear_mask = eth['regime_consensus'] == 'bear'
print(f"熊市总样本数: {bear_mask.sum()}")

for sig_col, sig_name in signals.items():
    mask = bear_mask & (eth[sig_col] == 1)
    signal_df = eth[mask]

    if len(signal_df) > 0:
        ret_48h = signal_df['future_48h'].dropna()
        if len(ret_48h) > 0:
            winrate = (ret_48h > 0).mean() * 100
            mean_ret = ret_48h.mean() * 100

            # 判断是否值得使用
            worth = "可用" if mean_ret > 0.5 and winrate > 50 else "谨慎" if mean_ret > 0 else "避免"
            print(f"{sig_name:30s}: N={len(ret_48h):<4}, 48H={mean_ret:>6.2f}%, 胜率={winrate:.1f}%, [{worth}]")
        else:
            print(f"{sig_name:30s}: 无有效样本")
    else:
        print(f"{sig_name:30s}: 熊市无信号")

# =============================================================================
# 8. 策略在震荡市的表现
# =============================================================================
print("\n" + "="*80)
print("策略在震荡市(neutral)的表现")
print("="*80)

neutral_mask = eth['regime_consensus'] == 'neutral'
print(f"震荡市总样本数: {neutral_mask.sum()}")

for sig_col, sig_name in signals.items():
    mask = neutral_mask & (eth[sig_col] == 1)
    signal_df = eth[mask]

    if len(signal_df) > 0:
        ret_48h = signal_df['future_48h'].dropna()
        if len(ret_48h) > 0:
            winrate = (ret_48h > 0).mean() * 100
            mean_ret = ret_48h.mean() * 100

            worth = "可用" if mean_ret > 0.5 and winrate > 50 else "谨慎" if mean_ret > 0 else "避免"
            print(f"{sig_name:30s}: N={len(ret_48h):<4}, 48H={mean_ret:>6.2f}%, 胜率={winrate:.1f}%, [{worth}]")
        else:
            print(f"{sig_name:30s}: 无有效样本")
    else:
        print(f"{sig_name:30s}: 震荡市无信号")

# =============================================================================
# 9. 寻找全天候信号
# =============================================================================
print("\n" + "="*80)
print("寻找全天候可用的信号特征")
print("="*80)

# 分析研究9在各状态下的子条件表现
print("\n--- 研究9条件拆解分析 ---")

# 简化的回调信号
eth['simple_pullback'] = (
    (eth['drawdown_48h'] <= -0.07) &
    (eth['price_chg_4h'] >= 0.015)
).astype(int)

# 加趋势过滤
eth['pullback_trend'] = (
    (eth['drawdown_48h'] <= -0.07) &
    (eth['price_chg_4h'] >= 0.015) &
    (eth['ma20'] > eth['ma50'])
).astype(int)

# 只要求价格在MA120以上
eth['pullback_above_ma120'] = (
    (eth['drawdown_48h'] <= -0.07) &
    (eth['price_chg_4h'] >= 0.015) &
    (eth['close'] > eth['ma120'])
).astype(int)

# 更深的回调
eth['deep_pullback'] = (
    (eth['drawdown_48h'] <= -0.10) &
    (eth['price_chg_4h'] >= 0.02)
).astype(int)

test_signals = {
    'simple_pullback': '简单回调(回撤7%+4H动量1.5%)',
    'pullback_trend': '回调+短期趋势(MA20>MA50)',
    'pullback_above_ma120': '回调+中期趋势(价格>MA120)',
    'deep_pullback': '深度回调(回撤10%+4H动量2%)'
}

for sig_col, sig_name in test_signals.items():
    print(f"\n【{sig_name}】")
    for regime in ['bull', 'neutral', 'bear']:
        mask = (eth['regime_consensus'] == regime) & (eth[sig_col] == 1)
        ret = eth.loc[mask, 'future_48h'].dropna()
        if len(ret) > 0:
            print(f"  {regime:8s}: N={len(ret):<4}, 48H={ret.mean()*100:>6.2f}%, 胜率={(ret>0).mean()*100:.1f}%")

# =============================================================================
# 10. 策略切换机制探索
# =============================================================================
print("\n" + "="*80)
print("策略切换机制探索")
print("="*80)

# 模拟策略切换: 牛市用研究9，熊市不交易或用简单策略
def simulate_regime_switch(df):
    """模拟市场状态切换策略"""
    results = {}

    # 策略1: 全天候使用研究9
    mask = df['signal_r9'] == 1
    ret = df.loc[mask, 'future_48h'].dropna()
    results['全天候R9'] = {
        'count': len(ret),
        'mean': ret.mean() * 100 if len(ret) > 0 else 0,
        'winrate': (ret > 0).mean() * 100 if len(ret) > 0 else 0
    }

    # 策略2: 只在牛市使用研究9
    mask = (df['signal_r9'] == 1) & (df['regime_consensus'] == 'bull')
    ret = df.loc[mask, 'future_48h'].dropna()
    results['仅牛市R9'] = {
        'count': len(ret),
        'mean': ret.mean() * 100 if len(ret) > 0 else 0,
        'winrate': (ret > 0).mean() * 100 if len(ret) > 0 else 0
    }

    # 策略3: 牛市+震荡市使用研究9
    mask = (df['signal_r9'] == 1) & (df['regime_consensus'].isin(['bull', 'neutral']))
    ret = df.loc[mask, 'future_48h'].dropna()
    results['非熊市R9'] = {
        'count': len(ret),
        'mean': ret.mean() * 100 if len(ret) > 0 else 0,
        'winrate': (ret > 0).mean() * 100 if len(ret) > 0 else 0
    }

    # 策略4: 牛市用R9，熊市用深回调
    bull_mask = (df['signal_r9'] == 1) & (df['regime_consensus'] == 'bull')
    bear_mask = (df['deep_pullback'] == 1) & (df['regime_consensus'] == 'bear')
    combined_mask = bull_mask | bear_mask
    ret = df.loc[combined_mask, 'future_48h'].dropna()
    results['牛R9+熊深回调'] = {
        'count': len(ret),
        'mean': ret.mean() * 100 if len(ret) > 0 else 0,
        'winrate': (ret > 0).mean() * 100 if len(ret) > 0 else 0
    }

    return results

switch_results = simulate_regime_switch(eth)

print("\n策略切换效果对比:")
print("-" * 60)
print(f"{'策略':<20} {'信号数':<8} {'48H收益':<12} {'胜率':<8}")
print("-" * 60)
for name, stats in switch_results.items():
    print(f"{name:<20} {stats['count']:<8} {stats['mean']:>8.2f}%    {stats['winrate']:.1f}%")

# =============================================================================
# 11. ADX趋势判断的有效性
# =============================================================================
print("\n" + "="*80)
print("ADX趋势判断的有效性")
print("="*80)

# 分析ADX阈值
print("\n--- 不同ADX阈值下的基准收益 ---")
for adx_threshold in [15, 20, 25, 30, 35]:
    # 趋势市
    trend_mask = eth['adx'] >= adx_threshold
    ret_trend = eth.loc[trend_mask, 'future_48h'].dropna()

    # 震荡市
    range_mask = eth['adx'] < adx_threshold
    ret_range = eth.loc[range_mask, 'future_48h'].dropna()

    if len(ret_trend) > 0 and len(ret_range) > 0:
        print(f"ADX>={adx_threshold}: 趋势市N={len(ret_trend)}, 48H={ret_trend.mean()*100:.2f}% | 震荡市N={len(ret_range)}, 48H={ret_range.mean()*100:.2f}%")

# ADX + DI方向
print("\n--- ADX + DI方向 ---")
for adx_threshold in [20, 25, 30]:
    # 上涨趋势
    up_trend = (eth['adx'] >= adx_threshold) & (eth['plus_di'] > eth['minus_di'])
    ret_up = eth.loc[up_trend, 'future_48h'].dropna()

    # 下跌趋势
    down_trend = (eth['adx'] >= adx_threshold) & (eth['minus_di'] > eth['plus_di'])
    ret_down = eth.loc[down_trend, 'future_48h'].dropna()

    if len(ret_up) > 0 and len(ret_down) > 0:
        print(f"ADX>={adx_threshold}: 上涨趋势48H={ret_up.mean()*100:.2f}%({len(ret_up)}) | 下跌趋势48H={ret_down.mean()*100:.2f}%({len(ret_down)})")

# =============================================================================
# 12. 市场状态持续时间分析
# =============================================================================
print("\n" + "="*80)
print("市场状态持续时间分析")
print("="*80)

def analyze_regime_duration(df, regime_col):
    """分析市场状态的持续时间"""
    df = df.copy()
    df['regime_change'] = (df[regime_col] != df[regime_col].shift(1)).astype(int)
    df['regime_group'] = df['regime_change'].cumsum()

    durations = df.groupby(['regime_group', regime_col]).size().reset_index(name='duration_hours')

    stats = durations.groupby(regime_col)['duration_hours'].agg(['mean', 'median', 'max', 'count'])
    return stats

duration_stats = analyze_regime_duration(eth, 'regime_consensus')
print("\n市场状态持续时间统计 (小时):")
print(duration_stats)

# =============================================================================
# 13. 状态转换分析
# =============================================================================
print("\n" + "="*80)
print("市场状态转换分析")
print("="*80)

# 分析状态转换后的收益
eth['prev_regime'] = eth['regime_consensus'].shift(1)
eth['regime_changed'] = (eth['regime_consensus'] != eth['prev_regime']).astype(int)

print("\n--- 状态转换后的48H收益 ---")
for from_regime in ['bull', 'neutral', 'bear']:
    for to_regime in ['bull', 'neutral', 'bear']:
        if from_regime != to_regime:
            mask = (eth['prev_regime'] == from_regime) & (eth['regime_consensus'] == to_regime)
            ret = eth.loc[mask, 'future_48h'].dropna()
            if len(ret) >= 10:
                print(f"{from_regime} -> {to_regime}: N={len(ret):<4}, 48H={ret.mean()*100:>6.2f}%, 胜率={(ret>0).mean()*100:.1f}%")

# =============================================================================
# 14. 总结
# =============================================================================
print("\n" + "="*80)
print("研究总结")
print("="*80)

summary = """
【市场状态识别】
1. 综合判断方法(均线+收益率+价格位置)效果较好
2. 牛市/熊市/震荡市的划分对策略选择有明显指导意义
3. ADX+DI可作为辅助判断工具

【各状态下策略表现】
1. 牛市: 几乎所有做多策略都有效，研究9表现最优
2. 熊市: 多数做多策略失效，需要谨慎或避免
3. 震荡市: 部分策略仍可使用，但收益下降

【策略适应性】
1. 研究9在牛市表现优异，但在熊市需要规避
2. 深度回调信号(10%+)在各状态下相对稳健
3. 放量突破策略在熊市风险较高

【策略切换机制】
1. 最简单有效: 熊市不交易
2. 进阶方案: 根据市场状态选择不同策略
3. 建议: 实盘中加入市场状态判断作为前置过滤器

【Phase 3建议】
1. 熊市可考虑做空策略，而非继续做多
2. 震荡市可使用更保守的信号阈值
3. 状态切换时应降低仓位或暂停交易
"""

print(summary)

print("\n研究完成!")
