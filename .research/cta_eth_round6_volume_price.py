"""
【CTA-ETH-研究6】量价关系做多信号研究

研究目标:
1. 放量上涨信号(价格涨+成交量放大)
2. 缩量回调后的放量突破
3. OBV趋势确认(OBV新高配合价格新高)
4. 成交量异常检测(异常放量)
5. Taker买卖数据分析(主动买入占比)
"""

import pickle
import pandas as pd
import numpy as np
from pathlib import Path

# 数据路径
DATA_PATH = Path("/Users/zhangjunmengyang/Downloads/coin-binance-spot-swap-preprocess-pkl-1h-2026-01-19")

# 加载数据
print("加载数据...")
with open(DATA_PATH / "swap_dict.pkl", "rb") as f:
    swap_dict = pickle.load(f)

eth = swap_dict["ETH-USDT"].copy()
print(f"ETH数据: {len(eth)} 行, {eth.index[0]} 到 {eth.index[-1]}")
print(f"列: {list(eth.columns)}")

# 计算未来收益
for h in [6, 12, 24, 48]:
    eth[f'ret_{h}h'] = eth['close'].shift(-h) / eth['close'] - 1

# ============================================================
# 1. 放量上涨信号研究
# ============================================================
print("\n" + "="*60)
print("1. 放量上涨信号研究")
print("="*60)

# 计算价格变化和成交量比率
eth['price_chg'] = eth['close'] / eth['close'].shift(1) - 1
eth['vol_ratio_24'] = eth['quote_volume'] / eth['quote_volume'].rolling(24, min_periods=1).mean()
eth['vol_ratio_48'] = eth['quote_volume'] / eth['quote_volume'].rolling(48, min_periods=1).mean()

# 放量上涨定义: 价格上涨 + 成交量高于均值
def test_volume_up_signal(vol_threshold, price_threshold, vol_window, holding_period):
    """测试放量上涨信号"""
    vol_ratio = eth['quote_volume'] / eth['quote_volume'].rolling(vol_window, min_periods=1).mean()
    signal = (eth['price_chg'] > price_threshold) & (vol_ratio > vol_threshold)

    ret_col = f'ret_{holding_period}h'
    sig_returns = eth.loc[signal, ret_col].dropna()
    all_returns = eth[ret_col].dropna()

    return {
        'count': len(sig_returns),
        'mean': sig_returns.mean() * 100 if len(sig_returns) > 0 else 0,
        'std': sig_returns.std() * 100 if len(sig_returns) > 0 else 0,
        'win_rate': (sig_returns > 0).mean() * 100 if len(sig_returns) > 0 else 0,
        'baseline': all_returns.mean() * 100
    }

print("\n放量上涨信号参数扫描 (48H持仓):")
print("-" * 70)
print(f"{'成交量阈值':<12} {'价格阈值':<12} {'信号数':<10} {'收益率':<12} {'胜率':<10}")
print("-" * 70)

best_vol_up = None
best_vol_up_return = -999

for vol_thresh in [1.2, 1.5, 2.0, 2.5, 3.0]:
    for price_thresh in [0.005, 0.01, 0.015, 0.02]:
        result = test_volume_up_signal(vol_thresh, price_thresh, 24, 48)
        if result['count'] >= 50:
            print(f"{vol_thresh:<12} {price_thresh*100:.1f}%{'':<8} {result['count']:<10} {result['mean']:.2f}%{'':<8} {result['win_rate']:.1f}%")
            if result['mean'] > best_vol_up_return:
                best_vol_up_return = result['mean']
                best_vol_up = {'vol': vol_thresh, 'price': price_thresh, 'result': result}

if best_vol_up:
    print(f"\n最优放量上涨参数: 成交量>{best_vol_up['vol']}x, 价格>{best_vol_up['price']*100}%")
    print(f"48H收益: {best_vol_up['result']['mean']:.2f}%, 胜率: {best_vol_up['result']['win_rate']:.1f}%")

# ============================================================
# 2. 缩量回调后放量突破
# ============================================================
print("\n" + "="*60)
print("2. 缩量回调后放量突破")
print("="*60)

def test_pullback_breakout(pullback_days, vol_contract_thresh, breakout_vol_thresh, holding_period):
    """
    缩量回调后放量突破:
    1. 过去N天内有缩量回调(成交量<均值*contract_thresh, 价格下跌)
    2. 当前放量突破(成交量>均值*breakout_thresh, 价格上涨)
    """
    vol_ratio = eth['quote_volume'] / eth['quote_volume'].rolling(24, min_periods=1).mean()

    # 缩量回调: 成交量缩小+价格下跌
    pullback = (vol_ratio < vol_contract_thresh) & (eth['price_chg'] < 0)
    pullback_in_window = pullback.rolling(pullback_days, min_periods=1).max().astype(bool)

    # 放量上涨
    breakout = (vol_ratio > breakout_vol_thresh) & (eth['price_chg'] > 0.005)

    # 组合信号
    signal = pullback_in_window.shift(1) & breakout

    ret_col = f'ret_{holding_period}h'
    sig_returns = eth.loc[signal, ret_col].dropna()

    return {
        'count': len(sig_returns),
        'mean': sig_returns.mean() * 100 if len(sig_returns) > 0 else 0,
        'win_rate': (sig_returns > 0).mean() * 100 if len(sig_returns) > 0 else 0
    }

print("\n缩量回调后放量突破参数扫描 (48H持仓):")
print("-" * 80)
print(f"{'回调窗口':<10} {'缩量阈值':<10} {'放量阈值':<10} {'信号数':<10} {'收益率':<12} {'胜率':<10}")
print("-" * 80)

best_pullback = None
best_pullback_return = -999

for pullback_days in [6, 12, 24]:
    for contract in [0.6, 0.7, 0.8]:
        for breakout in [1.3, 1.5, 2.0]:
            result = test_pullback_breakout(pullback_days, contract, breakout, 48)
            if result['count'] >= 30:
                print(f"{pullback_days:<10} {contract:<10} {breakout:<10} {result['count']:<10} {result['mean']:.2f}%{'':<8} {result['win_rate']:.1f}%")
                if result['mean'] > best_pullback_return:
                    best_pullback_return = result['mean']
                    best_pullback = {'days': pullback_days, 'contract': contract, 'breakout': breakout, 'result': result}

if best_pullback:
    print(f"\n最优缩量回调参数: 窗口={best_pullback['days']}h, 缩量<{best_pullback['contract']}x, 放量>{best_pullback['breakout']}x")
    print(f"48H收益: {best_pullback['result']['mean']:.2f}%, 胜率: {best_pullback['result']['win_rate']:.1f}%")

# ============================================================
# 3. OBV趋势确认
# ============================================================
print("\n" + "="*60)
print("3. OBV趋势确认")
print("="*60)

# 计算OBV
eth['obv'] = (np.sign(eth['close'].diff()) * eth['volume']).cumsum()
eth['obv_ema_12'] = eth['obv'].ewm(span=12, adjust=False).mean()
eth['obv_ema_26'] = eth['obv'].ewm(span=26, adjust=False).mean()

# 价格EMA
eth['price_ema_12'] = eth['close'].ewm(span=12, adjust=False).mean()
eth['price_ema_26'] = eth['close'].ewm(span=26, adjust=False).mean()

# OBV新高
eth['obv_high_24'] = eth['obv'].rolling(24, min_periods=1).max()
eth['obv_high_48'] = eth['obv'].rolling(48, min_periods=1).max()
eth['price_high_24'] = eth['close'].rolling(24, min_periods=1).max()
eth['price_high_48'] = eth['close'].rolling(48, min_periods=1).max()

def test_obv_signal(signal_type, lookback, holding_period):
    """测试OBV信号"""
    if signal_type == 'obv_ema_cross':
        # OBV EMA金叉
        signal = (eth['obv_ema_12'] > eth['obv_ema_26']) & (eth['obv_ema_12'].shift(1) <= eth['obv_ema_26'].shift(1))
    elif signal_type == 'obv_price_new_high':
        # OBV和价格同时创新高
        obv_high = eth['obv'].rolling(lookback, min_periods=1).max()
        price_high = eth['close'].rolling(lookback, min_periods=1).max()
        signal = (eth['obv'] >= obv_high) & (eth['close'] >= price_high)
    elif signal_type == 'obv_lead_price':
        # OBV先创新高，价格还未创新高(OBV领先)
        obv_high = eth['obv'].rolling(lookback, min_periods=1).max()
        price_high = eth['close'].rolling(lookback, min_periods=1).max()
        signal = (eth['obv'] >= obv_high) & (eth['close'] < price_high * 0.98)
    elif signal_type == 'obv_trend_up':
        # OBV趋势向上(短期EMA>长期EMA)且价格金叉
        obv_up = eth['obv_ema_12'] > eth['obv_ema_26']
        price_cross = (eth['price_ema_12'] > eth['price_ema_26']) & (eth['price_ema_12'].shift(1) <= eth['price_ema_26'].shift(1))
        signal = obv_up & price_cross
    else:
        return None

    ret_col = f'ret_{holding_period}h'
    sig_returns = eth.loc[signal, ret_col].dropna()

    return {
        'count': len(sig_returns),
        'mean': sig_returns.mean() * 100 if len(sig_returns) > 0 else 0,
        'win_rate': (sig_returns > 0).mean() * 100 if len(sig_returns) > 0 else 0
    }

print("\nOBV信号测试 (48H持仓):")
print("-" * 60)

obv_signals = [
    ('OBV EMA金叉(12/26)', 'obv_ema_cross', 0),
    ('OBV+价格同创24H新高', 'obv_price_new_high', 24),
    ('OBV+价格同创48H新高', 'obv_price_new_high', 48),
    ('OBV领先价格(24H)', 'obv_lead_price', 24),
    ('OBV领先价格(48H)', 'obv_lead_price', 48),
    ('OBV趋势+价格金叉', 'obv_trend_up', 0),
]

best_obv = None
best_obv_return = -999

for name, sig_type, lookback in obv_signals:
    result = test_obv_signal(sig_type, lookback, 48)
    if result and result['count'] >= 20:
        print(f"{name:<25} 信号数:{result['count']:<6} 收益:{result['mean']:.2f}%  胜率:{result['win_rate']:.1f}%")
        if result['mean'] > best_obv_return:
            best_obv_return = result['mean']
            best_obv = {'name': name, 'type': sig_type, 'lookback': lookback, 'result': result}

if best_obv:
    print(f"\n最优OBV信号: {best_obv['name']}")
    print(f"48H收益: {best_obv['result']['mean']:.2f}%, 胜率: {best_obv['result']['win_rate']:.1f}%")

# ============================================================
# 4. 成交量异常检测
# ============================================================
print("\n" + "="*60)
print("4. 成交量异常检测")
print("="*60)

# 计算成交量Z-score
for window in [24, 48, 72]:
    vol_mean = eth['quote_volume'].rolling(window, min_periods=1).mean()
    vol_std = eth['quote_volume'].rolling(window, min_periods=1).std()
    eth[f'vol_zscore_{window}'] = (eth['quote_volume'] - vol_mean) / (vol_std + 1e-8)

def test_volume_anomaly(z_threshold, window, require_price_up, holding_period):
    """测试成交量异常信号"""
    zscore = eth[f'vol_zscore_{window}']
    signal = zscore > z_threshold

    if require_price_up:
        signal = signal & (eth['price_chg'] > 0)

    ret_col = f'ret_{holding_period}h'
    sig_returns = eth.loc[signal, ret_col].dropna()

    return {
        'count': len(sig_returns),
        'mean': sig_returns.mean() * 100 if len(sig_returns) > 0 else 0,
        'win_rate': (sig_returns > 0).mean() * 100 if len(sig_returns) > 0 else 0
    }

print("\n成交量异常信号参数扫描 (48H持仓):")
print("-" * 70)
print(f"{'Z阈值':<10} {'窗口':<10} {'需价格涨':<10} {'信号数':<10} {'收益率':<12} {'胜率':<10}")
print("-" * 70)

best_anomaly = None
best_anomaly_return = -999

for z_thresh in [1.5, 2.0, 2.5, 3.0]:
    for window in [24, 48]:
        for price_up in [True, False]:
            result = test_volume_anomaly(z_thresh, window, price_up, 48)
            if result['count'] >= 20:
                price_str = "是" if price_up else "否"
                print(f"{z_thresh:<10} {window}h{'':<6} {price_str:<10} {result['count']:<10} {result['mean']:.2f}%{'':<8} {result['win_rate']:.1f}%")
                if result['mean'] > best_anomaly_return:
                    best_anomaly_return = result['mean']
                    best_anomaly = {'z': z_thresh, 'window': window, 'price_up': price_up, 'result': result}

if best_anomaly:
    price_str = "需要" if best_anomaly['price_up'] else "不需要"
    print(f"\n最优异常信号: Z>{best_anomaly['z']}, 窗口={best_anomaly['window']}h, {price_str}价格上涨")
    print(f"48H收益: {best_anomaly['result']['mean']:.2f}%, 胜率: {best_anomaly['result']['win_rate']:.1f}%")

# ============================================================
# 5. Taker买入占比分析
# ============================================================
print("\n" + "="*60)
print("5. Taker买入占比分析")
print("="*60)

# 计算Taker买入占比
eth['taker_buy_ratio'] = eth['taker_buy_quote_asset_volume'] / eth['quote_volume']
eth['taker_buy_ratio_ma_12'] = eth['taker_buy_ratio'].rolling(12, min_periods=1).mean()
eth['taker_buy_ratio_ma_24'] = eth['taker_buy_ratio'].rolling(24, min_periods=1).mean()

print(f"\nTaker买入占比统计:")
print(f"均值: {eth['taker_buy_ratio'].mean():.3f}")
print(f"标准差: {eth['taker_buy_ratio'].std():.3f}")
print(f"最小: {eth['taker_buy_ratio'].min():.3f}")
print(f"最大: {eth['taker_buy_ratio'].max():.3f}")

def test_taker_signal(signal_type, threshold, holding_period):
    """测试Taker买入信号"""
    if signal_type == 'high_ratio':
        # 高Taker买入占比
        signal = eth['taker_buy_ratio'] > threshold
    elif signal_type == 'ratio_cross_ma':
        # Taker占比突破均线
        signal = (eth['taker_buy_ratio'] > eth['taker_buy_ratio_ma_24']) & \
                 (eth['taker_buy_ratio'].shift(1) <= eth['taker_buy_ratio_ma_24'].shift(1))
    elif signal_type == 'high_ratio_vol_up':
        # 高Taker占比 + 放量
        vol_ratio = eth['quote_volume'] / eth['quote_volume'].rolling(24, min_periods=1).mean()
        signal = (eth['taker_buy_ratio'] > threshold) & (vol_ratio > 1.5)
    elif signal_type == 'ratio_trend_up':
        # Taker占比趋势向上
        signal = eth['taker_buy_ratio_ma_12'] > eth['taker_buy_ratio_ma_24']
    elif signal_type == 'extreme_high':
        # 极端高Taker占比(>75%分位)
        threshold_val = eth['taker_buy_ratio'].quantile(threshold)
        signal = eth['taker_buy_ratio'] > threshold_val
    else:
        return None

    ret_col = f'ret_{holding_period}h'
    sig_returns = eth.loc[signal, ret_col].dropna()

    return {
        'count': len(sig_returns),
        'mean': sig_returns.mean() * 100 if len(sig_returns) > 0 else 0,
        'win_rate': (sig_returns > 0).mean() * 100 if len(sig_returns) > 0 else 0
    }

print("\nTaker买入信号测试 (48H持仓):")
print("-" * 70)

taker_signals = [
    ('Taker占比>52%', 'high_ratio', 0.52),
    ('Taker占比>53%', 'high_ratio', 0.53),
    ('Taker占比>54%', 'high_ratio', 0.54),
    ('Taker占比突破24H均线', 'ratio_cross_ma', 0),
    ('高Taker+放量(>52%)', 'high_ratio_vol_up', 0.52),
    ('高Taker+放量(>53%)', 'high_ratio_vol_up', 0.53),
    ('Taker趋势向上(12>24)', 'ratio_trend_up', 0),
    ('Taker>75分位', 'extreme_high', 0.75),
    ('Taker>80分位', 'extreme_high', 0.80),
]

best_taker = None
best_taker_return = -999

for name, sig_type, threshold in taker_signals:
    result = test_taker_signal(sig_type, threshold, 48)
    if result and result['count'] >= 20:
        print(f"{name:<25} 信号数:{result['count']:<6} 收益:{result['mean']:.2f}%  胜率:{result['win_rate']:.1f}%")
        if result['mean'] > best_taker_return:
            best_taker_return = result['mean']
            best_taker = {'name': name, 'type': sig_type, 'threshold': threshold, 'result': result}

if best_taker:
    print(f"\n最优Taker信号: {best_taker['name']}")
    print(f"48H收益: {best_taker['result']['mean']:.2f}%, 胜率: {best_taker['result']['win_rate']:.1f}%")

# ============================================================
# 6. 综合量价信号
# ============================================================
print("\n" + "="*60)
print("6. 综合量价信号构建")
print("="*60)

# 基于以上研究构建综合信号
vol_ratio_24 = eth['quote_volume'] / eth['quote_volume'].rolling(24, min_periods=1).mean()

# 综合信号1: 放量上涨 + 高Taker占比
sig1 = (eth['price_chg'] > 0.01) & (vol_ratio_24 > 1.5) & (eth['taker_buy_ratio'] > 0.52)
result1 = eth.loc[sig1, 'ret_48h'].dropna()

# 综合信号2: OBV趋势向上 + 放量 + 高Taker
sig2 = (eth['obv_ema_12'] > eth['obv_ema_26']) & (vol_ratio_24 > 1.3) & (eth['taker_buy_ratio'] > 0.52)
result2 = eth.loc[sig2, 'ret_48h'].dropna()

# 综合信号3: 成交量异常 + 价格上涨 + OBV确认
sig3 = (eth['vol_zscore_24'] > 2.0) & (eth['price_chg'] > 0) & (eth['obv_ema_12'] > eth['obv_ema_26'])
result3 = eth.loc[sig3, 'ret_48h'].dropna()

# 综合信号4: 缩量回调后放量突破 + 高Taker
pullback = (vol_ratio_24 < 0.7) & (eth['price_chg'] < 0)
pullback_window = pullback.rolling(12, min_periods=1).max().astype(bool)
breakout = (vol_ratio_24 > 1.5) & (eth['price_chg'] > 0.005) & (eth['taker_buy_ratio'] > 0.52)
sig4 = pullback_window.shift(1) & breakout
result4 = eth.loc[sig4, 'ret_48h'].dropna()

print("\n综合信号测试结果 (48H持仓):")
print("-" * 70)
print(f"{'信号':<40} {'信号数':<10} {'收益率':<12} {'胜率':<10}")
print("-" * 70)

signals_combined = [
    ('放量上涨+高Taker(>1.5x,>1%,>52%)', result1),
    ('OBV趋势+放量+高Taker', result2),
    ('成交量异常(Z>2)+涨+OBV确认', result3),
    ('缩量回调后放量突破+高Taker', result4),
]

best_combined = None
best_combined_return = -999

for name, returns in signals_combined:
    if len(returns) >= 10:
        mean_ret = returns.mean() * 100
        win_rate = (returns > 0).mean() * 100
        print(f"{name:<40} {len(returns):<10} {mean_ret:.2f}%{'':<8} {win_rate:.1f}%")
        if mean_ret > best_combined_return:
            best_combined_return = mean_ret
            best_combined = {'name': name, 'count': len(returns), 'mean': mean_ret, 'win_rate': win_rate}

# ============================================================
# 7. 与前序研究的最优策略对比
# ============================================================
print("\n" + "="*60)
print("7. 与前序研究最优策略对比")
print("="*60)

# 研究5的增强版ADX+DI+EMA系统
# ADX>25, +DI>-DI, EMA12>EMA26, MFI>50
eth['tr'] = np.maximum(
    eth['high'] - eth['low'],
    np.maximum(
        abs(eth['high'] - eth['close'].shift(1)),
        abs(eth['low'] - eth['close'].shift(1))
    )
)
eth['atr_14'] = eth['tr'].rolling(14, min_periods=1).mean()

# +DI, -DI
eth['dm_plus'] = np.where(
    (eth['high'] - eth['high'].shift(1)) > (eth['low'].shift(1) - eth['low']),
    np.maximum(eth['high'] - eth['high'].shift(1), 0),
    0
)
eth['dm_minus'] = np.where(
    (eth['low'].shift(1) - eth['low']) > (eth['high'] - eth['high'].shift(1)),
    np.maximum(eth['low'].shift(1) - eth['low'], 0),
    0
)
eth['di_plus_14'] = 100 * eth['dm_plus'].rolling(14, min_periods=1).mean() / (eth['atr_14'] + 1e-8)
eth['di_minus_14'] = 100 * eth['dm_minus'].rolling(14, min_periods=1).mean() / (eth['atr_14'] + 1e-8)

# ADX
eth['dx'] = 100 * abs(eth['di_plus_14'] - eth['di_minus_14']) / (eth['di_plus_14'] + eth['di_minus_14'] + 1e-8)
eth['adx_14'] = eth['dx'].rolling(14, min_periods=1).mean()

# MFI
typical_price = (eth['high'] + eth['low'] + eth['close']) / 3
raw_mf = typical_price * eth['volume']
mf_positive = np.where(typical_price > typical_price.shift(1), raw_mf, 0)
mf_negative = np.where(typical_price < typical_price.shift(1), raw_mf, 0)
mf_pos_sum = pd.Series(mf_positive).rolling(14, min_periods=1).sum()
mf_neg_sum = pd.Series(mf_negative).rolling(14, min_periods=1).sum()
eth['mfi_14'] = 100 - 100 / (1 + mf_pos_sum / (mf_neg_sum + 1e-8))

# 研究5增强版策略
sig_r5 = (eth['adx_14'] > 25) & (eth['di_plus_14'] > eth['di_minus_14']) & \
         (eth['price_ema_12'] > eth['price_ema_26']) & (eth['mfi_14'] > 50)
result_r5 = eth.loc[sig_r5, 'ret_48h'].dropna()

print(f"\n研究5增强版(ADX+DI+EMA+MFI): 信号数={len(result_r5)}, 收益={result_r5.mean()*100:.2f}%, 胜率={(result_r5>0).mean()*100:.1f}%")

# 量价增强版: 研究5基础 + 放量确认
sig_enhanced = sig_r5 & (vol_ratio_24 > 1.2)
result_enhanced = eth.loc[sig_enhanced, 'ret_48h'].dropna()
print(f"研究5+放量确认(>1.2x): 信号数={len(result_enhanced)}, 收益={result_enhanced.mean()*100:.2f}%, 胜率={(result_enhanced>0).mean()*100:.1f}%")

# 量价增强版2: 研究5基础 + 高Taker
sig_enhanced2 = sig_r5 & (eth['taker_buy_ratio'] > 0.52)
result_enhanced2 = eth.loc[sig_enhanced2, 'ret_48h'].dropna()
print(f"研究5+高Taker(>52%): 信号数={len(result_enhanced2)}, 收益={result_enhanced2.mean()*100:.2f}%, 胜率={(result_enhanced2>0).mean()*100:.1f}%")

# 量价增强版3: 研究5基础 + 放量 + 高Taker
sig_enhanced3 = sig_r5 & (vol_ratio_24 > 1.2) & (eth['taker_buy_ratio'] > 0.52)
result_enhanced3 = eth.loc[sig_enhanced3, 'ret_48h'].dropna()
print(f"研究5+放量+高Taker: 信号数={len(result_enhanced3)}, 收益={result_enhanced3.mean()*100:.2f}%, 胜率={(result_enhanced3>0).mean()*100:.1f}%")

# ============================================================
# 8. 总结
# ============================================================
print("\n" + "="*60)
print("8. 研究总结")
print("="*60)

baseline = eth['ret_48h'].dropna().mean() * 100
print(f"\n基准(全样本48H均值): {baseline:.2f}%")

print("\n各类量价信号最优结果:")
if best_vol_up:
    print(f"1. 放量上涨: {best_vol_up['result']['mean']:.2f}% (成交量>{best_vol_up['vol']}x, 价格>{best_vol_up['price']*100}%)")
if best_pullback:
    print(f"2. 缩量回调后放量突破: {best_pullback['result']['mean']:.2f}%")
if best_obv:
    print(f"3. OBV信号({best_obv['name']}): {best_obv['result']['mean']:.2f}%")
if best_anomaly:
    print(f"4. 成交量异常(Z>{best_anomaly['z']}): {best_anomaly['result']['mean']:.2f}%")
if best_taker:
    print(f"5. Taker信号({best_taker['name']}): {best_taker['result']['mean']:.2f}%")
if best_combined:
    print(f"6. 综合信号({best_combined['name']}): {best_combined['mean']:.2f}%")

print(f"\n研究5增强版基础: {result_r5.mean()*100:.2f}%")
print(f"研究5+放量确认: {result_enhanced.mean()*100:.2f}%")
print(f"研究5+高Taker: {result_enhanced2.mean()*100:.2f}%")
print(f"研究5+放量+高Taker: {result_enhanced3.mean()*100:.2f}%")

print("\n研究完成!")
