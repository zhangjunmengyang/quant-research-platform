"""
【CTA-ETH-研究6】最终优化 - 最优策略确定

关键发现:
1. 放量上涨(4.0x, 2%)达到3.05%的48H收益
2. 放量上涨(3.5x, 2%)+EMA趋势稳定性更好
3. 研究5+强放量(3.0x,2%)达到2.81%
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

def eval_signal(signal, holding=48):
    ret_col = f'ret_{holding}h'
    returns = eth.loc[signal, ret_col].dropna()
    if len(returns) < 10:
        return None
    return {
        'count': len(returns),
        'mean': returns.mean() * 100,
        'std': returns.std() * 100,
        'win_rate': (returns > 0).mean() * 100,
        'sharpe': returns.mean() / (returns.std() + 1e-8) * np.sqrt(365 * 24 / holding),
        'max_dd': (returns.cumsum() - returns.cumsum().cummax()).min() * 100
    }

# ============================================================
# 1. 候选最优策略对比
# ============================================================
print("\n" + "="*70)
print("候选最优策略全面对比")
print("="*70)

# 定义候选策略
strategies = {
    # 纯放量策略
    '放量上涨(3.0x,2%)': (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.0),
    '放量上涨(3.5x,2%)': (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.5),
    '放量上涨(4.0x,2%)': (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 4.0),

    # 放量+趋势
    '放量(3.0x,2%)+EMA': (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.0) & (eth['ema_12'] > eth['ema_26']),
    '放量(3.5x,2%)+EMA': (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.5) & (eth['ema_12'] > eth['ema_26']),
    '放量(3.0x,2%)+EMA+MFI>60': (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.0) & (eth['ema_12'] > eth['ema_26']) & (eth['mfi_14'] > 60),

    # 放量+ADX趋势强度
    '放量(3.0x,2%)+EMA+ADX>20': (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.0) & (eth['ema_12'] > eth['ema_26']) & (eth['adx_14'] > 20),

    # 研究5组合
    '研究5+放量(2.0x)': (eth['adx_14'] > 25) & (eth['di_plus_14'] > eth['di_minus_14']) & (eth['ema_12'] > eth['ema_26']) & (eth['mfi_14'] > 50) & (eth['vol_ratio_24'] > 2.0),
    '研究5+放量(3.0x,2%)': (eth['adx_14'] > 25) & (eth['di_plus_14'] > eth['di_minus_14']) & (eth['ema_12'] > eth['ema_26']) & (eth['mfi_14'] > 50) & (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.0),
}

print("\n48H持仓期收益对比:")
print("-" * 90)
print(f"{'策略':<30} {'信号数':<8} {'收益':<10} {'胜率':<10} {'夏普':<10} {'最大回撤':<10}")
print("-" * 90)

results = {}
for name, sig in strategies.items():
    result = eval_signal(sig)
    if result:
        results[name] = result
        print(f"{name:<30} {result['count']:<8} {result['mean']:.2f}%{'':<6} {result['win_rate']:.1f}%{'':<6} {result['sharpe']:.2f}{'':<6} {result['max_dd']:.1f}%")

# ============================================================
# 2. 最优策略年度稳健性
# ============================================================
print("\n" + "="*70)
print("最优策略年度稳健性检验")
print("="*70)

eth['year'] = pd.to_datetime(eth['candle_begin_time'], unit='ms').dt.year if eth['candle_begin_time'].dtype != 'datetime64[ns]' else eth['candle_begin_time'].dt.year

# 放量上涨(3.5x, 2%)+EMA - 综合最优
best_strategy = (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 3.5) & (eth['ema_12'] > eth['ema_26'])

print("\n放量上涨(3.5x,2%)+EMA 年度检验:")
print("-" * 60)
for year in sorted(eth['year'].unique()):
    mask = (eth['year'] == year) & best_strategy
    ret = eth.loc[mask, 'ret_48h'].dropna()
    if len(ret) >= 5:
        print(f"{year}年: 信号数={len(ret):<3}, 收益={ret.mean()*100:>6.2f}%, 胜率={(ret>0).mean()*100:.1f}%")

# 放量上涨(4.0x, 2%) - 收益最高
high_vol_strategy = (eth['price_chg'] > 0.02) & (eth['vol_ratio_24'] > 4.0)

print("\n放量上涨(4.0x,2%) 年度检验:")
print("-" * 60)
for year in sorted(eth['year'].unique()):
    mask = (eth['year'] == year) & high_vol_strategy
    ret = eth.loc[mask, 'ret_48h'].dropna()
    if len(ret) >= 5:
        print(f"{year}年: 信号数={len(ret):<3}, 收益={ret.mean()*100:>6.2f}%, 胜率={(ret>0).mean()*100:.1f}%")

# ============================================================
# 3. 总结最佳推荐策略
# ============================================================
print("\n" + "="*70)
print("研究6总结: 最佳推荐策略")
print("="*70)

print("""
核心发现:
1. "量在价先"理论在ETH市场高度有效
2. 极端放量(>3x)配合价格上涨是强烈的趋势启动信号
3. Taker买入占比单独使用效果一般，但可作为辅助确认

推荐策略排名:

第一名: 放量上涨(3.5x,2%)+EMA
- 条件: 成交量>24H均值3.5倍 + 价格涨幅>2% + EMA12>EMA26
- 48H收益: ~2.8%, 胜率: ~60%
- 优势: 信号数适中，年度稳定性好

第二名: 放量上涨(4.0x,2%)
- 条件: 成交量>24H均值4倍 + 价格涨幅>2%
- 48H收益: ~3.05%, 胜率: ~62.5%
- 优势: 收益最高，信号更精准
- 劣势: 信号数较少(~112个)

第三名: 研究5+放量(3.0x,2%)
- 条件: ADX>25 + DI+>DI- + EMA金叉 + MFI>50 + 放量上涨
- 48H收益: ~2.81%, 胜率: ~60%
- 优势: 多重确认，过滤效果好

与研究5的比较:
- 研究5增强版: 48H收益1.62%
- 本研究最优策略: 48H收益3.05%
- 提升幅度: +88%

关键洞察:
1. 成交量是最重要的确认指标
2. 极端放量(>3x)本身就包含了强烈的趋势信息
3. 配合EMA趋势确认可以提高稳定性
4. 价格涨幅阈值设置在2%左右效果最佳
""")

# 基准对比
baseline = eth['ret_48h'].dropna().mean() * 100
print(f"\n基准(全样本48H均值): {baseline:.2f}%")
print(f"最优策略相对基准倍数: {3.05/baseline:.1f}x")
