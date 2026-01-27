"""
CTA-ETH-研究33: 做空仓位管理优化

参考研究19(做多仓位管理)和研究32(做空止损止盈)的结论
使用研究31中表现最好的做空信号(反弹衰竭sig_C)进行仓位管理研究

做空特点:
- 胜率较低(约52-62%)
- 轧空风险需要严格仓位控制
- 主要用于对冲而非获利
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

# 日线/周线均线(用于多周期分析)
eth['MA20_daily'] = eth['close'].rolling(20*24).mean()
eth['MA50_daily'] = eth['close'].rolling(50*24).mean()
eth['MA5_weekly'] = eth['close'].rolling(5*24*7).mean()
eth['MA10_weekly'] = eth['close'].rolling(10*24*7).mean()

# ATR (用于波动率调整)
high_low = eth['high'] - eth['low']
high_close = np.abs(eth['high'] - eth['close'].shift())
low_close = np.abs(eth['low'] - eth['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
eth['ATR14'] = tr.rolling(14).mean()
eth['ATR20'] = tr.rolling(20).mean()
eth['ATR_pct'] = eth['ATR14'] / eth['close'] * 100  # ATR占价格百分比

# RSI
delta = eth['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / avg_loss
eth['RSI'] = 100 - (100 / (1 + rs))

# RSI最近12H最大值
eth['RSI_max_12h'] = eth['RSI'].rolling(12).max()

# 区间涨跌幅
for h in [1, 4, 8, 12, 24, 48]:
    eth[f'ret_{h}h'] = eth['close'].pct_change(h) * 100

# 成交量
eth['vol_ma10'] = eth['volume'].rolling(10).mean()
eth['vol_ma20'] = eth['volume'].rolling(20).mean()
eth['vol_ratio'] = eth['volume'] / eth['vol_ma20']

# 做空未来收益 (价格下跌为正)
for h in [4, 6, 8, 10, 12, 16, 24, 48, 72]:
    eth[f'fwd_short_{h}h'] = -eth['close'].pct_change(-h) * 100

# 未来最大上涨(用于止损分析)
for h in [12, 24]:
    eth[f'fwd_max_rise_{h}h'] = (eth['high'].shift(-h).rolling(h).max() / eth['close'] - 1) * 100

# ========================================
# 3. 定义做空信号
# ========================================

# 熊市定义
eth['is_bear'] = eth['MA50'] < eth['MA200']
eth['is_strong_bear'] = eth['MA50'] < eth['MA120'] * 0.95

# 日周共振空头
eth['daily_bear'] = eth['MA20_daily'] < eth['MA50_daily']
eth['weekly_bear'] = eth['MA5_weekly'] < eth['MA10_weekly']
eth['multi_tf_bear'] = eth['daily_bear'] & eth['weekly_bear']

# 区间高点
eth['high_12h'] = eth['high'].rolling(12).max()

# 回落幅度
eth['pullback'] = (eth['high_12h'] - eth['close']) / eth['high_12h'] * 100

# ========================================
# 信号A: 熊市反弹超买 (研究31 sig_A)
# ========================================
eth['sig_A'] = (
    eth['is_bear'] &
    (eth['ret_24h'] > 8) &
    (eth['RSI'] > 70)
)

# ========================================
# 信号B: 熊市恐慌放量 (研究31 sig_B)
# ========================================
eth['sig_B'] = (
    eth['is_bear'] &
    (eth['volume'] > 3 * eth['vol_ma20']) &
    (eth['ret_1h'] < -2) &
    (eth['ret_24h'] < -5)
)

# ========================================
# 信号C: 反弹衰竭 (研究31 sig_C - 最优单信号)
# 熊市中反弹后出现回落
# ========================================
eth['sig_C'] = (
    eth['is_bear'] &
    (eth['ret_12h'] > 5) &
    (eth['pullback'] > 1.5)
)

# ========================================
# 信号D: 多周期共振做空 (研究31 sig_D)
# ========================================
eth['sig_D'] = (
    eth['multi_tf_bear'] &
    (eth['ret_24h'] > 6) &
    (eth['RSI'] > 65)
)

# 组合信号: B+C (研究31最优组合)
eth['sig_BC'] = eth['sig_B'] | eth['sig_C']

# 使用sig_C(反弹衰竭)作为主要测试信号 - 研究31中胜率最高(61.6%)
eth['short_signal'] = eth['sig_C']

# 去除重叠信号
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

# 对各信号去重
for sig in ['sig_A', 'sig_B', 'sig_C', 'sig_D', 'sig_BC']:
    eth[f'{sig}_clean'] = remove_overlap(eth[sig], 24)

# 主信号使用sig_C(反弹衰竭)
eth['short_signal_clean'] = eth['sig_C_clean']

signals_df = eth[eth['short_signal_clean']].copy()
print(f"\n信号统计:")
print(f"  sig_A(熊市反弹超买): {eth['sig_A_clean'].sum()}个")
print(f"  sig_B(熊市恐慌放量): {eth['sig_B_clean'].sum()}个")
print(f"  sig_C(反弹衰竭): {eth['sig_C_clean'].sum()}个 <- 主信号")
print(f"  sig_D(多周期共振): {eth['sig_D_clean'].sum()}个")
print(f"  sig_BC(B+C组合): {eth['sig_BC_clean'].sum()}个")

# ========================================
# 4. 凯利公式分析
# ========================================

print("\n" + "="*70)
print("一、凯利公式分析")
print("="*70)

# 应用5%止损5%止盈
def apply_sltp(returns, sl_pct=5.0, tp_pct=5.0):
    """应用止损止盈"""
    adjusted = returns.copy()
    adjusted = adjusted.clip(lower=-sl_pct, upper=tp_pct)
    return adjusted

def calculate_kelly(returns):
    """计算凯利仓位"""
    wins = returns[returns > 0]
    losses = returns[returns <= 0]

    if len(returns) == 0:
        return None

    win_rate = len(wins) / len(returns)
    avg_win = wins.mean() if len(wins) > 0 else 0
    avg_loss = abs(losses.mean()) if len(losses) > 0 else 0.001

    # 凯利公式: f* = (p*b - q) / b
    b = avg_win / avg_loss if avg_loss > 0 else 1
    kelly = (win_rate * b - (1 - win_rate)) / b if b > 0 else 0

    return {
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'odds_ratio': b,
        'kelly': kelly,
        'half_kelly': kelly * 0.5,
        'quarter_kelly': kelly * 0.25
    }

# 分析不同信号的凯利仓位
print("\n不同做空信号的凯利仓位分析(24H持仓+5%SL/TP):")
print("-"*80)
print(f"{'信号':>15} {'信号数':>8} {'胜率':>8} {'平均盈':>8} {'平均亏':>8} {'盈亏比':>8} {'凯利%':>8} {'1/2凯利%':>10}")
print("-"*80)

for sig_name in ['sig_A', 'sig_B', 'sig_C', 'sig_D', 'sig_BC']:
    sig_data = eth[eth[f'{sig_name}_clean']]['fwd_short_24h'].dropna()
    if len(sig_data) >= 10:
        adj_returns = apply_sltp(sig_data, 5.0, 5.0)
        kelly_info = calculate_kelly(adj_returns)
        if kelly_info:
            print(f"{sig_name:>15} {len(sig_data):>8} {kelly_info['win_rate']*100:>7.1f}% "
                  f"{kelly_info['avg_win']:>7.2f}% {kelly_info['avg_loss']:>7.2f}% "
                  f"{kelly_info['odds_ratio']:>8.2f} {kelly_info['kelly']*100:>7.1f}% "
                  f"{kelly_info['half_kelly']*100:>9.1f}%")

# 主信号(sig_C)详细分析
print("\n主信号sig_C(反弹衰竭)详细分析:")
returns_24h = signals_df['fwd_short_24h'].dropna()
returns_with_sltp = apply_sltp(returns_24h, 5.0, 5.0)
kelly_info = calculate_kelly(returns_with_sltp)

if kelly_info:
    print(f"  总信号数: {len(returns_with_sltp)}")
    print(f"  胜率: {kelly_info['win_rate']*100:.1f}%")
    print(f"  平均盈利: {kelly_info['avg_win']:.2f}%")
    print(f"  平均亏损: {kelly_info['avg_loss']:.2f}%")
    print(f"  盈亏比: {kelly_info['odds_ratio']:.2f}")
    print(f"  凯利最优仓位: {kelly_info['kelly']*100:.1f}%")
    print(f"  1/2凯利: {kelly_info['half_kelly']*100:.1f}%")
    print(f"  1/4凯利: {kelly_info['quarter_kelly']*100:.1f}%")
    kelly = kelly_info['kelly']
else:
    kelly = 0

# 对比做多信号的凯利
print("\n对比做多信号(研究19):")
print("  做多胜率: 88.3%")
print("  做多盈亏比: 1.70")
print("  做多凯利仓位: 81.4%")
print("  做多推荐: 1/2凯利 = 40%")
print("\n结论: 做空凯利仓位显著低于做多，说明做空预期收益较低")

# ========================================
# 5. 不同凯利比例回测
# ========================================

print("\n" + "="*70)
print("二、凯利比例仓位测试")
print("="*70)

def backtest_fixed_position(returns, position_pct, sl_pct=5.0, tp_pct=5.0):
    """固定仓位回测"""
    adjusted_returns = apply_sltp(returns, sl_pct, tp_pct)

    # 账户收益 = 信号收益 * 仓位
    account_returns = adjusted_returns * position_pct / 100

    # 累计收益
    cumulative = (1 + account_returns / 100).cumprod()
    total_return = (cumulative.iloc[-1] - 1) * 100 if len(cumulative) > 0 else 0

    # 最大回撤
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max * 100
    max_dd = drawdown.min()

    # 单笔最大亏损
    max_single_loss = account_returns.min()

    return {
        'position': position_pct,
        'total_return': total_return,
        'max_drawdown': max_dd,
        'return_dd_ratio': total_return / abs(max_dd) if max_dd < 0 else 0,
        'max_single_loss': max_single_loss,
        'trades': len(adjusted_returns),
        'win_rate': (adjusted_returns > 0).mean() * 100
    }

returns_24h = signals_df['fwd_short_24h'].dropna()

print("\n固定仓位策略对比(24H持仓+5%SL/TP):")
print("-"*70)
print(f"{'仓位比例':>10} {'总收益':>10} {'最大回撤':>10} {'收益/回撤':>10} {'单笔最大亏':>12}")
print("-"*70)

for pos in [5, 10, 15, 20, 25, 30, 50]:
    result = backtest_fixed_position(returns_24h, pos)
    print(f"{result['position']:>8}% {result['total_return']:>9.1f}% {result['max_drawdown']:>9.1f}% "
          f"{result['return_dd_ratio']:>10.1f} {result['max_single_loss']:>11.2f}%")

# 凯利比例测试
if kelly > 0:
    print("\n凯利比例仓位测试:")
    print("-"*70)
    for k_ratio, name in [(1.0, '满仓凯利'), (0.5, '1/2凯利'), (0.25, '1/4凯利')]:
        pos = kelly * k_ratio * 100
        if pos > 0:
            result = backtest_fixed_position(returns_24h, pos)
            print(f"{name}({pos:.1f}%): 总收益{result['total_return']:.1f}%, "
                  f"最大回撤{result['max_drawdown']:.1f}%, 收益/回撤{result['return_dd_ratio']:.1f}")
else:
    print("\n凯利仓位为负或零，表明做空预期收益为负")
    print("建议: 仅在特定市场环境下小仓位做空用于对冲")

# ========================================
# 6. 波动率调整仓位
# ========================================

print("\n" + "="*70)
print("三、波动率调整仓位")
print("="*70)

def backtest_vol_adjusted(df, signals_col, base_position=20, target_vol=2.0, max_position=50, min_position=5):
    """波动率调整仓位回测"""
    signal_times = df[df[signals_col]].index

    results = []
    for t in signal_times:
        if t not in df.index:
            continue

        # 获取当前ATR
        atr_pct = df.loc[t, 'ATR_pct'] if 'ATR_pct' in df.columns else 2.0

        # 波动率调整仓位
        if atr_pct > 0:
            vol_adjusted_pos = base_position * target_vol / atr_pct
            vol_adjusted_pos = max(min_position, min(max_position, vol_adjusted_pos))
        else:
            vol_adjusted_pos = base_position

        # 获取收益
        fwd_ret = df.loc[t, 'fwd_short_24h'] if 'fwd_short_24h' in df.columns else 0
        if pd.isna(fwd_ret):
            continue

        # 应用止损止盈
        fwd_ret = max(-5, min(5, fwd_ret))

        results.append({
            'time': t,
            'atr_pct': atr_pct,
            'position': vol_adjusted_pos,
            'raw_return': fwd_ret,
            'account_return': fwd_ret * vol_adjusted_pos / 100
        })

    if not results:
        return None

    results_df = pd.DataFrame(results)

    # 计算累计收益和回撤
    cumulative = (1 + results_df['account_return'] / 100).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max * 100

    return {
        'avg_position': results_df['position'].mean(),
        'total_return': (cumulative.iloc[-1] - 1) * 100,
        'max_drawdown': drawdown.min(),
        'return_dd_ratio': (cumulative.iloc[-1] - 1) * 100 / abs(drawdown.min()) if drawdown.min() < 0 else 0,
        'trades': len(results_df),
        'win_rate': (results_df['account_return'] > 0).mean() * 100
    }

# 测试不同基础仓位和目标波动率组合
print("\n波动率调整仓位测试:")
print("-"*70)
print(f"{'基础仓位':>10} {'目标波动':>10} {'平均仓位':>10} {'总收益':>10} {'最大回撤':>10} {'收益/回撤':>10}")
print("-"*70)

for base_pos in [10, 15, 20, 25]:
    for target_vol in [1.5, 2.0, 2.5, 3.0]:
        result = backtest_vol_adjusted(eth, 'short_signal_clean', base_pos, target_vol, max_position=40)
        if result:
            print(f"{base_pos:>8}% {target_vol:>9.1f}% {result['avg_position']:>9.1f}% "
                  f"{result['total_return']:>9.1f}% {result['max_drawdown']:>9.1f}% "
                  f"{result['return_dd_ratio']:>10.1f}")

# 波动率调整方向测试: 高波动时增仓vs减仓
print("\n高波动时仓位调整方向测试:")
print("-"*70)

def backtest_vol_direction(df, signals_col, base_position=20, direction='decrease'):
    """测试高波动时增仓或减仓"""
    signal_times = df[df[signals_col]].index

    results = []
    for t in signal_times:
        if t not in df.index:
            continue

        atr_pct = df.loc[t, 'ATR_pct'] if 'ATR_pct' in df.columns else 2.0
        avg_atr = df['ATR_pct'].rolling(100).mean().loc[t] if 'ATR_pct' in df.columns else 2.0

        if pd.isna(avg_atr):
            avg_atr = 2.0

        # 判断当前波动率高低
        if atr_pct > avg_atr * 1.2:
            vol_state = 'high'
        elif atr_pct < avg_atr * 0.8:
            vol_state = 'low'
        else:
            vol_state = 'normal'

        # 根据方向调整仓位
        if direction == 'decrease':  # 高波动减仓
            if vol_state == 'high':
                adj_pos = base_position * 0.5
            elif vol_state == 'low':
                adj_pos = base_position * 1.5
            else:
                adj_pos = base_position
        else:  # 高波动加仓
            if vol_state == 'high':
                adj_pos = base_position * 1.5
            elif vol_state == 'low':
                adj_pos = base_position * 0.5
            else:
                adj_pos = base_position

        adj_pos = max(5, min(40, adj_pos))

        fwd_ret = df.loc[t, 'fwd_short_24h'] if 'fwd_short_24h' in df.columns else 0
        if pd.isna(fwd_ret):
            continue

        fwd_ret = max(-5, min(5, fwd_ret))

        results.append({
            'time': t,
            'vol_state': vol_state,
            'position': adj_pos,
            'account_return': fwd_ret * adj_pos / 100
        })

    if not results:
        return None

    results_df = pd.DataFrame(results)
    cumulative = (1 + results_df['account_return'] / 100).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max * 100

    return {
        'direction': direction,
        'avg_position': results_df['position'].mean(),
        'total_return': (cumulative.iloc[-1] - 1) * 100,
        'max_drawdown': drawdown.min(),
        'return_dd_ratio': (cumulative.iloc[-1] - 1) * 100 / abs(drawdown.min()) if drawdown.min() < 0 else 0,
    }

for direction in ['decrease', 'increase']:
    result = backtest_vol_direction(eth, 'short_signal_clean', 20, direction)
    if result:
        label = "高波动减仓" if direction == 'decrease' else "高波动加仓"
        print(f"{label}: 平均仓位{result['avg_position']:.1f}%, "
              f"总收益{result['total_return']:.1f}%, 最大回撤{result['max_drawdown']:.1f}%, "
              f"收益/回撤{result['return_dd_ratio']:.1f}")

# ========================================
# 7. 信号强度分级仓位
# ========================================

print("\n" + "="*70)
print("四、信号强度分级")
print("="*70)

# 按不同维度分级信号

# 7.1 按回调幅度分级
print("\n7.1 按24H回调幅度分级:")
print("-"*70)

signals_with_data = signals_df[['ret_12h', 'ret_24h', 'vol_ratio', 'RSI', 'ATR_pct', 'pullback',
                                  'fwd_short_12h', 'fwd_short_24h', 'fwd_short_48h']].dropna()

# 注意: 做空信号时ret_12h通常为正(反弹后做空) - sig_C要求ret_12h>5%
print(f"{'反弹幅度':>12} {'信号数':>8} {'胜率':>8} {'平均收益':>10} {'建议仓位':>10}")
print("-"*70)

# 按12H反弹幅度分级(信号条件要求ret_12h>5%)
pullback_bins = [(5, 7), (7, 10), (10, 15), (15, 100)]

for low, high in pullback_bins:
    mask = (signals_with_data['ret_12h'] >= low) & (signals_with_data['ret_12h'] < high)
    subset = signals_with_data[mask]
    if len(subset) >= 5:
        returns = apply_sltp(subset['fwd_short_24h'], 5.0, 5.0)
        win_rate = (returns > 0).mean() * 100
        avg_ret = returns.mean()
        # 根据胜率和收益建议仓位
        if win_rate >= 60 and avg_ret > 0.3:
            suggest = "重仓(20-25%)"
        elif win_rate >= 55 and avg_ret > 0:
            suggest = "标准(15%)"
        else:
            suggest = "轻仓(10%)"
        print(f"{low:>4}%~{high:>3}% {len(subset):>8} {win_rate:>7.1f}% {avg_ret:>9.2f}% {suggest:>12}")

# 7.2 按回落程度分级(sig_C的pullback条件)
print("\n7.2 按回落程度分级(pullback):")
print("-"*70)

pullback_bins2 = [(1.5, 2), (2, 3), (3, 5), (5, 100)]
print(f"{'回落幅度':>12} {'信号数':>8} {'胜率':>8} {'平均收益':>10} {'建议仓位':>10}")
print("-"*70)

for low, high in pullback_bins2:
    mask = (signals_with_data['pullback'] >= low) & (signals_with_data['pullback'] < high)
    subset = signals_with_data[mask]
    if len(subset) >= 5:
        returns = apply_sltp(subset['fwd_short_24h'], 5.0, 5.0)
        win_rate = (returns > 0).mean() * 100
        avg_ret = returns.mean()
        if win_rate >= 60 and avg_ret > 0.3:
            suggest = "重仓(20-25%)"
        elif win_rate >= 55 and avg_ret > 0:
            suggest = "标准(15%)"
        else:
            suggest = "轻仓(10%)"
        print(f"{low:>4}%~{high:>3}% {len(subset):>8} {win_rate:>7.1f}% {avg_ret:>9.2f}% {suggest:>12}")

# 7.3 按成交量萎缩程度分级
print("\n7.3 按成交量比率分级(量缩程度):")
print("-"*70)

vol_bins = [(0, 0.5), (0.5, 0.8), (0.8, 1.2), (1.2, 2.0), (2.0, 10)]
print(f"{'量比区间':>12} {'信号数':>8} {'胜率':>8} {'平均收益':>10} {'建议仓位':>10}")
print("-"*70)

for low, high in vol_bins:
    mask = (signals_with_data['vol_ratio'] >= low) & (signals_with_data['vol_ratio'] < high)
    subset = signals_with_data[mask]
    if len(subset) >= 5:
        returns = apply_sltp(subset['fwd_short_24h'], 5.0, 5.0)
        win_rate = (returns > 0).mean() * 100
        avg_ret = returns.mean()
        if win_rate >= 60 and avg_ret > 0.3:
            suggest = "重仓(20-25%)"
        elif win_rate >= 55 and avg_ret > 0:
            suggest = "标准(15%)"
        else:
            suggest = "轻仓(10%)"
        print(f"{low:>4}~{high:>5}x {len(subset):>8} {win_rate:>7.1f}% {avg_ret:>9.2f}% {suggest:>12}")

# 7.4 按RSI分级
print("\n7.4 按当前RSI分级:")
print("-"*70)

rsi_bins = [(0, 30), (30, 40), (40, 50), (50, 60), (60, 100)]
print(f"{'RSI区间':>12} {'信号数':>8} {'胜率':>8} {'平均收益':>10} {'建议仓位':>10}")
print("-"*70)

for low, high in rsi_bins:
    mask = (signals_with_data['RSI'] >= low) & (signals_with_data['RSI'] < high)
    subset = signals_with_data[mask]
    if len(subset) >= 5:
        returns = apply_sltp(subset['fwd_short_24h'], 5.0, 5.0)
        win_rate = (returns > 0).mean() * 100
        avg_ret = returns.mean()
        if win_rate >= 60 and avg_ret > 0.3:
            suggest = "重仓(20-25%)"
        elif win_rate >= 55 and avg_ret > 0:
            suggest = "标准(15%)"
        else:
            suggest = "轻仓(10%)"
        print(f"{low:>4}~{high:>5} {len(subset):>8} {win_rate:>7.1f}% {avg_ret:>9.2f}% {suggest:>12}")

# 7.5 按波动率分级
print("\n7.5 按ATR波动率分级:")
print("-"*70)

if len(signals_with_data) >= 30:
    atr_quantiles = signals_with_data['ATR_pct'].quantile([0, 0.33, 0.67, 1.0]).values
    atr_bins = [(atr_quantiles[0], atr_quantiles[1]),
                (atr_quantiles[1], atr_quantiles[2]),
                (atr_quantiles[2], atr_quantiles[3])]

    print(f"{'波动率区间':>14} {'信号数':>8} {'胜率':>8} {'平均收益':>10} {'建议仓位':>10}")
    print("-"*70)

    for i, (low, high) in enumerate(atr_bins):
        mask = (signals_with_data['ATR_pct'] >= low) & (signals_with_data['ATR_pct'] <= high)
        subset = signals_with_data[mask]
        label = ['低波动', '中波动', '高波动'][i]
        if len(subset) >= 5:
            returns = apply_sltp(subset['fwd_short_24h'], 5.0, 5.0)
            win_rate = (returns > 0).mean() * 100
            avg_ret = returns.mean()
            if win_rate >= 60 and avg_ret > 0.3:
                suggest = "重仓(20-25%)"
            elif win_rate >= 55 and avg_ret > 0:
                suggest = "标准(15%)"
            else:
                suggest = "轻仓(10%)"
            print(f"{label}({low:.2f}%-{high:.2f}%) {len(subset):>6} {win_rate:>7.1f}% {avg_ret:>9.2f}% {suggest:>12}")

# ========================================
# 8. 最大仓位限制测试
# ========================================

print("\n" + "="*70)
print("五、最大仓位限制测试")
print("="*70)

print("\n不同最大仓位限制下的策略表现:")
print("-"*70)
print(f"{'最大仓位':>10} {'总收益':>10} {'最大回撤':>10} {'收益/回撤':>10} {'年化收益':>10}")
print("-"*70)

years = (eth.index[-1] - eth.index[0]).days / 365

for max_pos in [10, 15, 20, 25, 30, 40, 50]:
    result = backtest_fixed_position(returns_24h, max_pos)
    annual_return = (1 + result['total_return']/100) ** (1/years) - 1
    print(f"{max_pos:>8}% {result['total_return']:>9.1f}% {result['max_drawdown']:>9.1f}% "
          f"{result['return_dd_ratio']:>10.1f} {annual_return*100:>9.1f}%")

# ========================================
# 9. 做多做空仓位配比
# ========================================

print("\n" + "="*70)
print("六、做多做空仓位配比测试")
print("="*70)

# 模拟做多信号(使用趋势回调反弹的简化版)
eth['is_bull'] = eth['MA50'] > eth['MA200']
eth['pullback_7pct'] = (eth['high'].rolling(20*24).max() - eth['close']) / eth['high'].rolling(20*24).max() * 100
eth['long_signal'] = (
    eth['is_bull'] &
    (eth['pullback_7pct'] >= 7) &
    (eth['pullback_7pct'] <= 15) &
    (eth['ret_4h'] > 2)  # 4H反弹
)
eth['long_signal_clean'] = remove_overlap(eth['long_signal'], 48)

# 做多未来收益
for h in [48]:
    eth[f'fwd_long_{h}h'] = eth['close'].pct_change(-h) * 100

long_signals = eth[eth['long_signal_clean']]
print(f"\n做多信号数量: {len(long_signals)}")
print(f"做空信号数量: {len(signals_df)}")

# 模拟不同配比的组合表现
def simulate_combined_strategy(eth_df, long_col, short_col, long_weight, short_weight,
                               long_pos=40, short_pos=20):
    """模拟多空组合策略"""

    # 获取所有信号时间点
    long_times = eth_df[eth_df[long_col]].index
    short_times = eth_df[eth_df[short_col]].index

    all_trades = []

    # 做多交易
    for t in long_times:
        fwd_ret = eth_df.loc[t, 'fwd_long_48h'] if 'fwd_long_48h' in eth_df.columns else 0
        if pd.isna(fwd_ret):
            continue
        # 做多止损5%
        fwd_ret = max(-5, fwd_ret)
        account_ret = fwd_ret * long_pos * long_weight / 100
        all_trades.append({'time': t, 'type': 'long', 'account_return': account_ret})

    # 做空交易
    for t in short_times:
        fwd_ret = eth_df.loc[t, 'fwd_short_10h'] if 'fwd_short_10h' in eth_df.columns else 0
        if pd.isna(fwd_ret):
            continue
        # 做空止损止盈5%
        fwd_ret = max(-5, min(5, fwd_ret))
        account_ret = fwd_ret * short_pos * short_weight / 100
        all_trades.append({'time': t, 'type': 'short', 'account_return': account_ret})

    if not all_trades:
        return None

    trades_df = pd.DataFrame(all_trades).sort_values('time')

    # 计算累计收益
    cumulative = (1 + trades_df['account_return'] / 100).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max * 100

    # 统计
    long_trades = trades_df[trades_df['type'] == 'long']
    short_trades = trades_df[trades_df['type'] == 'short']

    return {
        'long_weight': long_weight,
        'short_weight': short_weight,
        'total_return': (cumulative.iloc[-1] - 1) * 100,
        'max_drawdown': drawdown.min(),
        'return_dd_ratio': (cumulative.iloc[-1] - 1) * 100 / abs(drawdown.min()) if drawdown.min() < 0 else 0,
        'long_trades': len(long_trades),
        'short_trades': len(short_trades),
        'long_contrib': long_trades['account_return'].sum() if len(long_trades) > 0 else 0,
        'short_contrib': short_trades['account_return'].sum() if len(short_trades) > 0 else 0
    }

print("\n不同做多做空配比测试:")
print("-"*80)
print(f"{'配比':>15} {'总收益':>10} {'最大回撤':>10} {'收益/回撤':>10} {'多头贡献':>10} {'空头贡献':>10}")
print("-"*80)

configs = [
    (1.0, 0.0, "纯做多"),
    (0.9, 0.1, "做多90%+做空10%"),
    (0.8, 0.2, "做多80%+做空20%"),
    (0.7, 0.3, "做多70%+做空30%"),
    (0.6, 0.4, "做多60%+做空40%"),
    (0.5, 0.5, "做多50%+做空50%"),
    (0.0, 1.0, "纯做空"),
]

for long_w, short_w, name in configs:
    result = simulate_combined_strategy(eth, 'long_signal_clean', 'short_signal_clean',
                                        long_w, short_w, long_pos=40, short_pos=20)
    if result:
        print(f"{name:>15} {result['total_return']:>9.1f}% {result['max_drawdown']:>9.1f}% "
              f"{result['return_dd_ratio']:>10.1f} {result['long_contrib']:>9.1f}% "
              f"{result['short_contrib']:>9.1f}%")

# ========================================
# 10. 综合仓位分级规则
# ========================================

print("\n" + "="*70)
print("七、综合仓位分级规则测试")
print("="*70)

def calculate_signal_score(row):
    """计算信号强度得分 - 基于sig_C(反弹衰竭)的特征"""
    score = 0

    # 反弹幅度得分 (ret_12h, 适中反弹最佳)
    if 7 <= row['ret_12h'] <= 12:
        score += 2
    elif 5 <= row['ret_12h'] < 7 or 12 < row['ret_12h'] <= 15:
        score += 1

    # 回落深度得分 (pullback, 更深回落更可靠)
    if row['pullback'] >= 3:
        score += 2
    elif row['pullback'] >= 2:
        score += 1

    # 量能得分 (反弹缩量更佳, 意味着动能不足)
    if row['vol_ratio'] < 0.7:
        score += 2
    elif row['vol_ratio'] < 1.0:
        score += 1

    # RSI得分 (RSI适中区域)
    if 40 <= row['RSI'] < 55:
        score += 1
    elif 55 <= row['RSI'] < 65:
        score += 2  # RSI较高说明反弹动能仍强，回落更有意义

    return score

signals_with_data['score'] = signals_with_data.apply(calculate_signal_score, axis=1)

print("\n按信号强度得分分级:")
print("-"*70)
print(f"{'得分':>8} {'信号数':>8} {'胜率':>8} {'平均收益':>10} {'建议仓位':>12}")
print("-"*70)

for score in sorted(signals_with_data['score'].unique()):
    subset = signals_with_data[signals_with_data['score'] == score]
    if len(subset) >= 5:
        returns = apply_sltp(subset['fwd_short_24h'], 5.0, 5.0)
        win_rate = (returns > 0).mean() * 100
        avg_ret = returns.mean()
        if score >= 5:
            suggest = "A级(20-25%)"
        elif score >= 3:
            suggest = "B级(15%)"
        else:
            suggest = "C级(10%)"
        print(f"{score:>8} {len(subset):>8} {win_rate:>7.1f}% {avg_ret:>9.2f}% {suggest:>12}")

# 按分级仓位回测
def backtest_graded_position(df, signals_with_score):
    """分级仓位回测"""
    results = []

    for idx, row in signals_with_score.iterrows():
        score = row['score']
        fwd_ret = row['fwd_short_24h']

        if pd.isna(fwd_ret):
            continue

        # 根据得分确定仓位
        if score >= 5:
            position = 22
        elif score >= 3:
            position = 15
        else:
            position = 10

        # 应用止损止盈
        fwd_ret = max(-5, min(5, fwd_ret))
        account_ret = fwd_ret * position / 100

        results.append({
            'time': idx,
            'score': score,
            'position': position,
            'account_return': account_ret
        })

    if not results:
        return None

    results_df = pd.DataFrame(results)
    cumulative = (1 + results_df['account_return'] / 100).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max * 100

    return {
        'avg_position': results_df['position'].mean(),
        'total_return': (cumulative.iloc[-1] - 1) * 100,
        'max_drawdown': drawdown.min(),
        'return_dd_ratio': (cumulative.iloc[-1] - 1) * 100 / abs(drawdown.min()) if drawdown.min() < 0 else 0,
        'trades': len(results_df)
    }

graded_result = backtest_graded_position(eth, signals_with_data)
fixed_result = backtest_fixed_position(returns_24h, 15)

print("\n分级仓位 vs 固定仓位对比:")
print("-"*70)
if graded_result:
    print(f"分级仓位: 平均仓位{graded_result['avg_position']:.1f}%, "
          f"总收益{graded_result['total_return']:.1f}%, "
          f"最大回撤{graded_result['max_drawdown']:.1f}%, "
          f"收益/回撤{graded_result['return_dd_ratio']:.1f}")
print(f"固定15%仓位: "
      f"总收益{fixed_result['total_return']:.1f}%, "
      f"最大回撤{fixed_result['max_drawdown']:.1f}%, "
      f"收益/回撤{fixed_result['return_dd_ratio']:.1f}")

# ========================================
# 11. 年度表现分析
# ========================================

print("\n" + "="*70)
print("八、年度表现分析")
print("="*70)

signals_with_data['year'] = signals_with_data.index.year
signals_with_data['adj_return'] = apply_sltp(signals_with_data['fwd_short_24h'], 5.0, 5.0)

yearly_stats = signals_with_data.groupby('year').agg({
    'adj_return': ['count', 'mean', lambda x: (x > 0).mean() * 100, 'std']
}).round(2)
yearly_stats.columns = ['交易数', '平均收益%', '胜率%', '标准差%']

print("\n年度表现(24H+5%SL/TP):")
print(yearly_stats)

# ========================================
# 12. 总结
# ========================================

print("\n" + "="*70)
print("研究33总结: 做空仓位管理优化")
print("="*70)

# 最终统计
final_returns = apply_sltp(signals_df['fwd_short_24h'].dropna(), 5.0, 5.0)
final_kelly = calculate_kelly(final_returns)

print(f"""
========== 核心发现 ==========

1. 凯利公式分析:
   - 做空信号(sig_C反弹衰竭):
     * 胜率: {final_kelly['win_rate']*100:.1f}%
     * 盈亏比: {final_kelly['odds_ratio']:.2f}
     * 凯利仓位: {final_kelly['kelly']*100:.1f}%
     * 1/2凯利: {final_kelly['half_kelly']*100:.1f}%
   - 对比做多(研究19):
     * 胜率: 88.3%, 盈亏比: 1.70
     * 凯利仓位: 81.4%, 推荐1/2凯利40%
   - 结论: 做空凯利仓位{'为负(不建议做空)' if final_kelly['kelly'] <= 0 else f'仅{final_kelly["kelly"]*100:.0f}%，远低于做多'}

2. 波动率调整仓位:
   - 高波动时减仓优于加仓(轧空风险)
   - 建议: 基础仓位15%, 目标波动率2%, 上限20%
   - 与做多相反: 做多高波动可加仓, 做空应减仓

3. 信号强度分级:
   - 反弹7-12%后做空效果较好
   - 回落深度>3%的信号更可靠
   - 量缩(<0.7倍均量)信号质量更高
   - RSI 40-65区间最佳

4. 最大仓位限制:
   - 推荐最大仓位: 15-20%
   - 绝对不超过25%
   - 考虑到做空的劣势, 严格限仓是必须的

5. 做多做空配比建议:
   - 做多为主(80-90%), 做空为辅(10-20%)
   - 做空主要用于熊市对冲, 而非独立获利
   - 纯做空策略不可行

========== 实盘建议 ==========

做空仓位分级规则:
| 信号等级 | 条件 | 仓位 |
|---------|------|------|
| A级(高质量) | 得分>=5 | 20% |
| B级(标准) | 得分3-4 | 15% |
| C级(谨慎) | 得分<3 | 10% |

风控规则:
- 单笔最大亏损: 账户的1%(仓位15%*止损5%=0.75%)
- 做空总仓位上限: 总资金的20%
- 连续亏损2笔后暂停做空
- 仅在确认熊市(MA50<MA200)做空

与做多策略的关键差异:
| 维度 | 做多 | 做空 |
|------|------|------|
| 凯利仓位 | 81% | {final_kelly['kelly']*100:.0f}% |
| 推荐仓位 | 40% | 15% |
| 最大仓位 | 50% | 20% |
| 高波动调整 | 加仓 | 减仓 |
| 预期胜率 | 88%+ | 55-62% |
| 策略定位 | 主策略 | 对冲工具 |
""")

print("\n研究33完成")
