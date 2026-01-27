"""
【CTA-ETH-研究6】深度分析 - 放量上涨信号优化

上一轮发现: 放量上涨(3.0x, 2.0%)的48H收益达到1.98%
本轮目标: 进一步优化参数，并尝试组合其他条件
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
print(f"ETH数据: {len(eth)} 行")

# 计算未来收益
for h in [6, 12, 24, 48, 72]:
    eth[f'ret_{h}h'] = eth['close'].shift(-h) / eth['close'] - 1

# 基础指标
eth['price_chg'] = eth['close'] / eth['close'].shift(1) - 1
eth['vol_ratio_24'] = eth['quote_volume'] / eth['quote_volume'].rolling(24, min_periods=1).mean()
eth['taker_buy_ratio'] = eth['taker_buy_quote_asset_volume'] / eth['quote_volume']

# EMA
eth['ema_12'] = eth['close'].ewm(span=12, adjust=False).mean()
eth['ema_26'] = eth['close'].ewm(span=26, adjust=False).mean()

# OBV
eth['obv'] = (np.sign(eth['close'].diff()) * eth['volume']).cumsum()
eth['obv_ema_12'] = eth['obv'].ewm(span=12, adjust=False).mean()
eth['obv_ema_26'] = eth['obv'].ewm(span=26, adjust=False).mean()

# MFI
typical_price = (eth['high'] + eth['low'] + eth['close']) / 3
raw_mf = typical_price * eth['volume']
mf_positive = np.where(typical_price > typical_price.shift(1), raw_mf, 0)
mf_negative = np.where(typical_price < typical_price.shift(1), raw_mf, 0)
mf_pos_sum = pd.Series(mf_positive).rolling(14, min_periods=1).sum()
mf_neg_sum = pd.Series(mf_negative).rolling(14, min_periods=1).sum()
eth['mfi_14'] = 100 - 100 / (1 + mf_pos_sum / (mf_neg_sum + 1e-8))

# ADX, DI
eth['tr'] = np.maximum(
    eth['high'] - eth['low'],
    np.maximum(
        abs(eth['high'] - eth['close'].shift(1)),
        abs(eth['low'] - eth['close'].shift(1))
    )
)
eth['atr_14'] = eth['tr'].rolling(14, min_periods=1).mean()
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
eth['dx'] = 100 * abs(eth['di_plus_14'] - eth['di_minus_14']) / (eth['di_plus_14'] + eth['di_minus_14'] + 1e-8)
eth['adx_14'] = eth['dx'].rolling(14, min_periods=1).mean()

# RSI
delta = eth['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14, min_periods=1).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14, min_periods=1).mean()
eth['rsi_14'] = 100 - 100 / (1 + gain / (loss + 1e-8))

# ============================================================
# 1. 放量上涨信号精细参数扫描
# ============================================================
print("\n" + "="*60)
print("1. 放量上涨信号精细参数扫描")
print("="*60)

def eval_signal(signal, holding=48):
    ret_col = f'ret_{holding}h'
    returns = eth.loc[signal, ret_col].dropna()
    if len(returns) < 20:
        return None
    return {
        'count': len(returns),
        'mean': returns.mean() * 100,
        'std': returns.std() * 100,
        'win_rate': (returns > 0).mean() * 100,
        'sharpe': returns.mean() / (returns.std() + 1e-8) * np.sqrt(365 * 24 / holding)
    }

print("\n放量上涨精细扫描 (48H持仓):")
print("-" * 80)
print(f"{'成交量阈值':<12} {'价格阈值':<12} {'信号数':<10} {'收益率':<12} {'胜率':<10} {'夏普':<10}")
print("-" * 80)

best_vol_up = None
best_vol_up_return = -999

for vol_thresh in [2.5, 2.8, 3.0, 3.2, 3.5, 4.0]:
    for price_thresh in [0.015, 0.018, 0.02, 0.022, 0.025, 0.03]:
        signal = (eth['price_chg'] > price_thresh) & (eth['vol_ratio_24'] > vol_thresh)
        result = eval_signal(signal)
        if result:
            print(f"{vol_thresh:<12} {price_thresh*100:.1f}%{'':<8} {result['count']:<10} {result['mean']:.2f}%{'':<8} {result['win_rate']:.1f}%{'':<6} {result['sharpe']:.2f}")
            if result['mean'] > best_vol_up_return and result['count'] >= 100:
                best_vol_up_return = result['mean']
                best_vol_up = {'vol': vol_thresh, 'price': price_thresh, 'result': result}

if best_vol_up:
    print(f"\n最优: 成交量>{best_vol_up['vol']}x, 价格>{best_vol_up['price']*100}% -> 收益={best_vol_up['result']['mean']:.2f}%")

# ============================================================
# 2. 放量上涨 + 趋势确认
# ============================================================
print("\n" + "="*60)
print("2. 放量上涨 + 趋势确认")
print("="*60)

# 基础放量上涨信号
base_vol_up = (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.0)

print("\n放量上涨(>3.0x, >2%)组合测试 (48H持仓):")
print("-" * 70)

signals = [
    ('基础信号', base_vol_up),
    ('+EMA趋势(12>26)', base_vol_up & (eth['ema_12'] > eth['ema_26'])),
    ('+OBV趋势', base_vol_up & (eth['obv_ema_12'] > eth['obv_ema_26'])),
    ('+MFI>50', base_vol_up & (eth['mfi_14'] > 50)),
    ('+MFI>60', base_vol_up & (eth['mfi_14'] > 60)),
    ('+RSI 40-70', base_vol_up & (eth['rsi_14'] > 40) & (eth['rsi_14'] < 70)),
    ('+ADX>20', base_vol_up & (eth['adx_14'] > 20)),
    ('+ADX>25', base_vol_up & (eth['adx_14'] > 25)),
    ('+DI+(>DI-)', base_vol_up & (eth['di_plus_14'] > eth['di_minus_14'])),
    ('+高Taker(>52%)', base_vol_up & (eth['taker_buy_ratio'] > 0.52)),
    ('+EMA+MFI>50', base_vol_up & (eth['ema_12'] > eth['ema_26']) & (eth['mfi_14'] > 50)),
    ('+EMA+OBV', base_vol_up & (eth['ema_12'] > eth['ema_26']) & (eth['obv_ema_12'] > eth['obv_ema_26'])),
    ('+EMA+ADX>20', base_vol_up & (eth['ema_12'] > eth['ema_26']) & (eth['adx_14'] > 20)),
    ('+EMA+高Taker', base_vol_up & (eth['ema_12'] > eth['ema_26']) & (eth['taker_buy_ratio'] > 0.52)),
]

best_combo = None
best_combo_return = -999

for name, sig in signals:
    result = eval_signal(sig)
    if result:
        print(f"{name:<25} 信号数:{result['count']:<6} 收益:{result['mean']:.2f}%  胜率:{result['win_rate']:.1f}%  夏普:{result['sharpe']:.2f}")
        if result['mean'] > best_combo_return and result['count'] >= 50:
            best_combo_return = result['mean']
            best_combo = {'name': name, 'result': result}

# ============================================================
# 3. 极端放量信号研究
# ============================================================
print("\n" + "="*60)
print("3. 极端放量信号研究")
print("="*60)

print("\n极端放量(>4x)参数测试:")
print("-" * 70)

for vol_thresh in [4.0, 5.0, 6.0]:
    for price_thresh in [0.01, 0.015, 0.02, 0.025]:
        signal = (eth['price_chg'] > price_thresh) & (eth['vol_ratio_24'] > vol_thresh)
        result = eval_signal(signal)
        if result and result['count'] >= 30:
            print(f"Vol>{vol_thresh}x, Price>{price_thresh*100}%: 信号数={result['count']}, 收益={result['mean']:.2f}%, 胜率={result['win_rate']:.1f}%")

# ============================================================
# 4. 连续放量信号
# ============================================================
print("\n" + "="*60)
print("4. 连续放量信号")
print("="*60)

# 连续N根K线放量
for n in [2, 3]:
    vol_above_avg = eth['vol_ratio_24'] > 1.5
    consecutive_vol = vol_above_avg.rolling(n, min_periods=n).sum() == n
    price_up_total = (eth['close'] / eth['close'].shift(n) - 1) > 0.02

    signal = consecutive_vol & price_up_total
    result = eval_signal(signal)
    if result:
        print(f"连续{n}根放量(>1.5x)+涨幅>2%: 信号数={result['count']}, 收益={result['mean']:.2f}%, 胜率={result['win_rate']:.1f}%")

# ============================================================
# 5. 放量上涨+研究5基础策略组合
# ============================================================
print("\n" + "="*60)
print("5. 放量上涨+研究5策略组合")
print("="*60)

# 研究5策略: ADX>25, DI+>DI-, EMA金叉, MFI>50
r5_base = (eth['adx_14'] > 25) & (eth['di_plus_14'] > eth['di_minus_14']) & \
          (eth['ema_12'] > eth['ema_26']) & (eth['mfi_14'] > 50)

# 放量上涨变体
vol_up_mild = (eth['price_chg'] > 0.01) & (eth['vol_ratio_24'] > 1.5)
vol_up_strong = (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.0)

print("\n研究5策略+放量组合 (48H持仓):")
print("-" * 70)

combinations = [
    ('研究5基础', r5_base),
    ('研究5+温和放量(1.5x,1%)', r5_base & vol_up_mild),
    ('研究5+强放量(3.0x,2%)', r5_base & vol_up_strong),
    ('研究5+放量>2x', r5_base & (eth['vol_ratio_24'] > 2.0)),
    ('研究5+高Taker+放量>1.5x', r5_base & (eth['taker_buy_ratio'] > 0.52) & (eth['vol_ratio_24'] > 1.5)),
]

for name, sig in combinations:
    result = eval_signal(sig)
    if result:
        print(f"{name:<30} 信号数:{result['count']:<6} 收益:{result['mean']:.2f}%  胜率:{result['win_rate']:.1f}%")

# ============================================================
# 6. 最终最优策略对比
# ============================================================
print("\n" + "="*60)
print("6. 最终策略对比")
print("="*60)

final_signals = {
    '基准(全样本)': eth.index.notnull(),  # 所有样本
    '放量上涨(3.0x,2%)': (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.0),
    '放量上涨(3.5x,2%)': (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.5),
    '放量上涨+EMA': (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.0) & (eth['ema_12'] > eth['ema_26']),
    '放量上涨+EMA+MFI': (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.0) & (eth['ema_12'] > eth['ema_26']) & (eth['mfi_14'] > 50),
    '研究5增强版': r5_base,
    '研究5+放量>2x': r5_base & (eth['vol_ratio_24'] > 2.0),
}

print("\n多周期收益对比:")
print("-" * 100)
print(f"{'策略':<25} {'信号数':<8} {'6H':<10} {'12H':<10} {'24H':<10} {'48H':<10} {'72H':<10}")
print("-" * 100)

for name, sig in final_signals.items():
    counts = len(eth.loc[sig, 'ret_48h'].dropna())
    if counts < 20 and name != '基准(全样本)':
        continue
    row = f"{name:<25} {counts:<8}"
    for h in [6, 12, 24, 48, 72]:
        ret = eth.loc[sig, f'ret_{h}h'].dropna()
        if len(ret) > 0:
            row += f" {ret.mean()*100:.2f}%{'':<5}"
        else:
            row += f" {'N/A':<9}"
    print(row)

# ============================================================
# 7. 信号稳健性分析 - 分年度检验
# ============================================================
print("\n" + "="*60)
print("7. 分年度稳健性检验 - 放量上涨(3.0x, 2%)")
print("="*60)

eth['year'] = pd.to_datetime(eth['candle_begin_time'], unit='ms').dt.year if eth['candle_begin_time'].dtype != 'datetime64[ns]' else eth['candle_begin_time'].dt.year

best_signal = (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.0)

print("\n按年度统计:")
print("-" * 60)
for year in sorted(eth['year'].unique()):
    mask = (eth['year'] == year) & best_signal
    ret = eth.loc[mask, 'ret_48h'].dropna()
    if len(ret) >= 10:
        print(f"{year}年: 信号数={len(ret)}, 收益={ret.mean()*100:.2f}%, 胜率={(ret>0).mean()*100:.1f}%")

# 放量上涨+EMA
best_signal_ema = (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.0) & (eth['ema_12'] > eth['ema_26'])
print("\n放量上涨+EMA 按年度统计:")
print("-" * 60)
for year in sorted(eth['year'].unique()):
    mask = (eth['year'] == year) & best_signal_ema
    ret = eth.loc[mask, 'ret_48h'].dropna()
    if len(ret) >= 10:
        print(f"{year}年: 信号数={len(ret)}, 收益={ret.mean()*100:.2f}%, 胜率={(ret>0).mean()*100:.1f}%")

print("\n研究完成!")
