"""
数据处理工具函数模块

包含因子分组分析、策略对比等数据处理函数。
"""

import os
import time
from functools import reduce
from itertools import combinations
from pathlib import Path
from typing import List, Union, Tuple, Dict, Any

import numpy as np
import pandas as pd


def _calculate_group_returns(
    df: pd.DataFrame,
    factor_name: str,
    bins: int,
    method: str = 'val'
) -> Tuple[List[str], pd.DataFrame]:
    """
    分组收益计算内部函数

    Args:
        df: 包含因子和收益数据的DataFrame
        factor_name: 因子列名
        bins: 分组数量
        method: 分组方法 'pct'(分位数) 或 'val'(等宽)

    Returns:
        (标签列表, 分组收益DataFrame)
    """
    df['total_coins'] = df.groupby('candle_begin_time')['symbol'].transform('size')
    valid_df = df[df['total_coins'] >= bins].copy()

    if method == 'pct':
        valid_df['rank'] = valid_df.groupby('candle_begin_time')[factor_name].rank(method='first')
        labels = [f'Group_{i}' for i in range(1, bins + 1)]
        valid_df['groups'] = valid_df.groupby('candle_begin_time')['rank'].transform(
            lambda x: pd.qcut(x, q=bins, labels=labels, duplicates='drop')
        )
    elif method == 'val':
        all_values = df[factor_name].dropna()
        if all_values.empty:
            raise ValueError("Factor data is empty, cannot calculate bins")
        _, bins_edges = pd.cut(all_values, bins=bins, retbins=True)
        labels = []
        for i in range(len(bins_edges) - 1):
            left_edge = round(bins_edges[i], 4)
            right_edge = round(bins_edges[i + 1], 4)
            left_bracket = '[' if i == 0 else '('
            labels.append(f'Group_{i + 1}{left_bracket}{left_edge}-{right_edge}]')
        valid_df['groups'] = pd.cut(
            valid_df[factor_name],
            bins=bins_edges,
            labels=labels,
            include_lowest=True,
            duplicates='drop'
        )

    valid_df['ret_next'] = valid_df['next_close'] / valid_df['close'] - 1
    group_returns = valid_df.groupby(['candle_begin_time', 'groups'])['ret_next'].mean().to_frame()
    group_returns.reset_index('groups', inplace=True)
    group_returns['groups'] = group_returns['groups'].astype(str)

    return labels, group_returns


def group_analysis(
    df: pd.DataFrame,
    factor_name: str,
    bins: int = 10,
    method: str = 'val'
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """
    因子分组分析

    Args:
        df: 包含分析数据的DataFrame，需要包含列:
            candle_begin_time, symbol, close, next_close, 以及因子列
        factor_name: 要分析的因子名称
        bins: 分组数量
        method: 分箱方法 'pct'(分位数) 或 'val'(等宽分箱)

    Returns:
        (分组累计净值曲线, 最终净值柱状图数据, 标签列表)

    Raises:
        ValueError: 输入数据不符合要求时抛出
    """
    if bins == 0:
        raise ValueError("bins cannot be 0")

    if method not in ['pct', 'val']:
        raise ValueError("method must be 'pct' or 'val'")

    required_columns = ['candle_begin_time', 'symbol', 'close', 'next_close']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        raise ValueError(f"Missing required columns: {missing}")

    labels, group_returns = _calculate_group_returns(df, factor_name, bins, method)

    group_returns = group_returns.reset_index()
    group_returns = pd.pivot(
        group_returns,
        index='candle_begin_time',
        columns='groups',
        values='ret_next'
    )
    group_curve = (group_returns + 1).cumprod()
    group_curve = group_curve[labels]

    first_bin_label = labels[0]
    last_bin_label = labels[-1]

    if group_curve[first_bin_label].iloc[-1] > group_curve[last_bin_label].iloc[-1]:
        ls_ret = (group_returns[first_bin_label] - group_returns[last_bin_label]) / 2
    else:
        ls_ret = (group_returns[last_bin_label] - group_returns[first_bin_label]) / 2

    group_curve['long_short_nav'] = (ls_ret + 1).cumprod()
    group_curve = group_curve.ffill()
    bar_df = group_curve.iloc[-1].reset_index()
    bar_df.columns = ['groups', 'asset']

    return group_curve, bar_df, labels


def coins_difference_all_pairs(
    root_path: Union[str, Path],
    strategies_list: List[str]
) -> List[Tuple[str, str, float]]:
    """
    计算所有策略两两之间的选币相似度

    Args:
        root_path: 根路径
        strategies_list: 策略名称列表

    Returns:
        相似度结果列表 [(策略1, 策略2, 相似度), ...]
    """
    root_path = Path(root_path)

    strategies = {}
    for strategy in strategies_list:
        s_path = root_path / f'data/backtest_results/{strategy}/final_select_results.pkl'
        s = pd.read_pickle(s_path)
        if s.empty:
            raise ValueError(f"{strategy} selection result is empty")
        s_grouped = s.groupby('candle_begin_time')['symbol'].apply(set).rename(strategy)
        strategies[strategy] = s_grouped

    df = pd.DataFrame(index=pd.Index([], name='candle_begin_time'))
    for strategy, s in strategies.items():
        df = df.join(s.rename(strategy), how='outer')
    df = df.reset_index()

    strategy_pairs = list(combinations(strategies_list, 2))
    results = []

    for strat1, strat2 in strategy_pairs:
        pair_df = df[['candle_begin_time', strat1, strat2]].copy()
        pair_df = pair_df.dropna()

        if pair_df.empty:
            results.append((strat1, strat2, np.nan))
            continue

        pair_df['intersection'] = pair_df.apply(lambda x: x[strat1] & x[strat2], axis=1)
        pair_df[f'{strat1}_count'] = pair_df[strat1].apply(len)
        pair_df[f'{strat2}_count'] = pair_df[strat2].apply(len)
        pair_df['overlap_count'] = pair_df['intersection'].apply(len)

        def calc_similarity(row, base_strat, other_strat):
            base_count = row[f'{base_strat}_count']
            other_count = row[f'{other_strat}_count']
            if base_count == 0:
                return 1.0 if other_count == 0 else np.nan
            return row['overlap_count'] / base_count

        pair_df[f'similarity_{strat1}'] = pair_df.apply(
            lambda x: calc_similarity(x, strat1, strat2), axis=1
        )
        pair_df[f'similarity_{strat2}'] = pair_df.apply(
            lambda x: calc_similarity(x, strat2, strat1), axis=1
        )
        similarity = np.nanmean(
            (pair_df[f'similarity_{strat1}'] + pair_df[f'similarity_{strat2}']) / 2
        )

        results.append((strat1, strat2, similarity))

    return results


def curve_difference_all_pairs(
    root_path: Union[str, Path],
    strategies_list: List[str]
) -> pd.DataFrame:
    """
    获取所有策略资金曲线结果

    Args:
        root_path: 根路径
        strategies_list: 策略名称列表

    Returns:
        包含所有策略涨跌幅的DataFrame
    """
    root_path = Path(root_path)

    strategies = {}
    for strategy in strategies_list:
        s_path = root_path / f'data/backtest_results/{strategy}/equity_curve.csv'
        s = pd.read_csv(s_path, encoding='utf-8-sig', parse_dates=['candle_begin_time'])
        if s.empty:
            raise ValueError(f"{strategy} equity curve is empty")
        s = s.rename(columns={'change_pct': f'{strategy}'})
        strategies[strategy] = s[['candle_begin_time', f'{strategy}']]

    df = reduce(
        lambda left, right: pd.merge(left, right, on='candle_begin_time', how='outer'),
        strategies.values()
    )

    return df.set_index('candle_begin_time')


def process_equity_data(
    root_path: Union[str, Path],
    backtest_name: str,
    start_time: str,
    end_time: str
) -> pd.DataFrame:
    """
    处理回测和实盘资金曲线数据，计算对比涨跌幅和资金曲线

    Args:
        root_path: 根路径
        backtest_name: 回测结果文件夹名称
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        包含回测和实盘资金曲线的DataFrame
    """
    root_path = Path(root_path)

    # 读取回测资金曲线
    backtest_equity = pd.read_csv(
        root_path / f'data/backtest_results/{backtest_name}/equity_curve.csv',
        encoding='utf-8-sig',
        parse_dates=['candle_begin_time']
    )

    backtest_equity = backtest_equity[
        (backtest_equity['candle_begin_time'] >= start_time) &
        (backtest_equity['candle_begin_time'] <= end_time)
    ]

    if backtest_equity.empty:
        raise ValueError("Backtest equity curve is empty for the given time range")

    backtest_equity['nav'] = backtest_equity['nav'] / backtest_equity['nav'].iloc[0]
    backtest_equity = backtest_equity.rename(
        columns={'change_pct': 'backtest_change', 'nav': 'backtest_nav', 'candle_begin_time': 'time'}
    )

    # 读取实盘资金曲线
    trading_equity = pd.read_csv(
        root_path / f'data/backtest_results/{backtest_name}/live_results/account/equity.csv',
        encoding='gbk',
        parse_dates=['time']
    )

    utc_offset = int(time.localtime().tm_gmtoff / 60 / 60) + 1
    trading_equity['time'] = trading_equity['time'] - pd.Timedelta(f'{utc_offset}H')
    trading_equity['time'] = trading_equity['time'].map(lambda x: x.strftime('%Y-%m-%d %H:00:00'))
    trading_equity['time'] = pd.to_datetime(trading_equity['time'])

    trading_equity = trading_equity[
        (trading_equity['time'] >= start_time) &
        (trading_equity['time'] <= end_time)
    ]

    if trading_equity.empty:
        raise ValueError("Live trading equity curve is empty for the given time range")

    trading_equity['live_nav'] = trading_equity['total_nav'] / trading_equity['total_nav'].iloc[0]
    trading_equity['live_change'] = trading_equity['live_nav'].pct_change()

    df = pd.merge(trading_equity, backtest_equity, on='time', how='inner')
    if df.empty:
        raise ValueError("Cannot align backtest and live trading time")

    df['comparison_change'] = (df['live_change'] - df['backtest_change']) / 2
    df['comparison_nav'] = (df['comparison_change'] + 1).cumprod()

    return df


def process_coin_selection_data(
    root_path: Union[str, Path],
    backtest_name: str,
    start_time: str,
    end_time: str
) -> pd.DataFrame:
    """
    处理回测和实盘选币数据，计算选币的交集、并集、相似度等指标

    Args:
        root_path: 根路径
        backtest_name: 回测结果文件夹名称
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        包含回测和实盘选币数据的DataFrame
    """
    root_path = Path(root_path)

    # 读取回测选币数据
    backtest_coins = pd.read_pickle(
        root_path / f'data/backtest_results/{backtest_name}/final_select_results.pkl'
    )
    backtest_coins = backtest_coins[
        (backtest_coins['candle_begin_time'] >= start_time) &
        (backtest_coins['candle_begin_time'] <= end_time)
    ]
    if backtest_coins.empty:
        raise ValueError("Backtest coin selection is empty for the given time range")

    backtest_coins['symbol'] = backtest_coins['symbol'].astype(str).apply(lambda x: x.replace('-', ''))

    # 读取实盘选币数据
    trading_coins = pd.DataFrame()
    path = root_path / f'data/backtest_results/{backtest_name}/live_results/select_coin'
    pkl_files = [f for f in os.listdir(path) if f.endswith('.pkl')]
    if len(pkl_files) == 0:
        raise ValueError("No live coin selection data found")

    for pkl_file in pkl_files:
        pkl_file_temp = pd.read_pickle(path / pkl_file)
        if pkl_file_temp.empty:
            raise ValueError(f"{pkl_file} is empty")
        trading_coins = pd.concat([trading_coins, pkl_file_temp], ignore_index=True)

    trading_coins['candle_begin_time'] = trading_coins['candle_begin_time'].map(
        lambda x: x.strftime('%Y-%m-%d %H:00:00')
    )
    trading_coins['candle_begin_time'] = pd.to_datetime(trading_coins['candle_begin_time'])

    trading_coins = trading_coins[
        (trading_coins['candle_begin_time'] >= start_time) &
        (trading_coins['candle_begin_time'] <= end_time)
    ]
    if trading_coins.empty:
        raise ValueError("Live coin selection is empty for the given time range")

    # 按时间分组并生成选币集合
    backtest_coins['symbol_type'] = backtest_coins['is_spot'].map({1: 'spot', 0: 'swap'})
    backtest_coins['direction'] = backtest_coins['direction'].astype(int)
    backtest_coins['coins_name'] = (
        backtest_coins['symbol'] + '(' +
        backtest_coins['symbol_type'] + ',' +
        backtest_coins['direction'].astype(str) + ')'
    )

    trading_coins['symbol_type'] = trading_coins['symbol_type'].astype(str)
    trading_coins['coins_name'] = (
        trading_coins['symbol'] + '(' +
        trading_coins['symbol_type'] + ',' +
        trading_coins['direction'].astype(str) + ')'
    )

    backtest_coins = backtest_coins.groupby('candle_begin_time').apply(
        lambda x: set(x['coins_name'])
    )
    backtest_coins = backtest_coins.to_frame().reset_index().rename(
        columns={0: f'backtest_{backtest_name}'}
    )

    trading_coins = trading_coins.groupby('candle_begin_time').apply(
        lambda x: set(x['coins_name'])
    )
    trading_coins = trading_coins.to_frame().reset_index().rename(
        columns={0: f'live_{backtest_name}'}
    )

    merged = pd.merge(backtest_coins, trading_coins, on='candle_begin_time', how='inner')
    if merged.empty:
        raise ValueError("Cannot align backtest and live coin selection time")

    # 计算指标
    merged['common_coins'] = merged.apply(
        lambda x: x[f'backtest_{backtest_name}'] & x[f'live_{backtest_name}'],
        axis=1
    )
    merged['backtest_only'] = merged.apply(
        lambda x: x[f'backtest_{backtest_name}'] - x['common_coins'],
        axis=1
    )
    merged['live_only'] = merged.apply(
        lambda x: x[f'live_{backtest_name}'] - x['common_coins'],
        axis=1
    )
    merged[f'backtest_{backtest_name}_count'] = merged[f'backtest_{backtest_name}'].str.len()
    merged[f'live_{backtest_name}_count'] = merged[f'live_{backtest_name}'].str.len()
    merged['overlap_count'] = merged['common_coins'].str.len()
    merged[f'similarity_backtest_{backtest_name}'] = (
        merged['common_coins'].str.len() / merged[f'backtest_{backtest_name}_count']
    )
    merged[f'similarity_live_{backtest_name}'] = (
        merged['common_coins'].str.len() / merged[f'live_{backtest_name}_count']
    )
    merged['similarity'] = (
        merged[f'similarity_backtest_{backtest_name}'] +
        merged[f'similarity_live_{backtest_name}']
    ) / 2

    return merged


def process_backtest_trading_factors(
    root_path: Union[str, Path],
    factors_name_list: List[str],
    backtest_name: str,
    coin: str
) -> Union[pd.DataFrame, bool]:
    """
    处理回测和实盘因子值对比数据

    Args:
        root_path: 根路径
        factors_name_list: 因子名称列表
        backtest_name: 回测名称
        coin: 币种名称

    Returns:
        合并后的因子值DataFrame，如果找不到币种返回False
    """
    root_path = Path(root_path)

    # 读取回测因子值
    backtest_kline = pd.read_pickle(root_path / 'data/cache/all_factors_kline.pkl')

    for factor_name in factors_name_list:
        path = root_path / 'data/cache' / f'factor_{factor_name}.pkl'
        factor = pd.read_pickle(path)
        if factor.empty:
            raise ValueError(f"{factor_name} backtest factor data is empty")
        backtest_kline[factor_name] = factor

    if backtest_kline.empty:
        raise ValueError("Backtest factor data is empty")

    # 读取实盘因子值
    trading_kline = pd.read_pickle(
        root_path / f'data/backtest_results/{backtest_name}/live_results/runtime/all_factors_kline.pkl'
    )
    for factor_name in factors_name_list:
        path = root_path / f'data/backtest_results/{backtest_name}/live_results/runtime/all_factors_{factor_name}.pkl'
        factor = pd.read_pickle(path)
        if factor.empty:
            raise ValueError(f"{factor_name} live factor data is empty")
        trading_kline[factor_name] = factor

    if trading_kline.empty:
        raise ValueError("Live factor data is empty")

    # 筛选币种数据
    backtest_kline['symbol'] = backtest_kline['symbol'].apply(lambda x: x.replace('-', ''))
    single_coin_backtest_kline = backtest_kline[backtest_kline['symbol'] == coin]
    single_coin_trading_kline = trading_kline[trading_kline['symbol'] == coin]

    if single_coin_backtest_kline.empty:
        return False
    if single_coin_trading_kline.empty:
        return False

    # 调整实盘时间
    single_coin_trading_kline['candle_begin_time'] = single_coin_trading_kline['candle_begin_time'].map(
        lambda x: x.strftime('%Y-%m-%d %H:00:00')
    )
    single_coin_trading_kline['candle_begin_time'] = pd.to_datetime(
        single_coin_trading_kline['candle_begin_time']
    )

    if set(single_coin_backtest_kline['candle_begin_time']).isdisjoint(
        set(single_coin_trading_kline['candle_begin_time'])
    ):
        raise ValueError("Live and backtest time have no overlap")

    single_coin_trading_kline['is_spot'] = single_coin_trading_kline['symbol_type'].map(
        {'spot': 1, 'swap': 0}
    )
    single_coin_backtest_kline['type'] = single_coin_backtest_kline['is_spot'].map({1: 'spot', 0: 'swap'})
    single_coin_trading_kline['type'] = single_coin_trading_kline['is_spot'].map({1: 'spot', 0: 'swap'})

    backtest_coin_type = set(single_coin_backtest_kline['type'])
    trading_coin_type = set(single_coin_trading_kline['type'])
    all_type = backtest_coin_type & trading_coin_type

    if backtest_coin_type != trading_coin_type:
        raise ValueError(
            f"Backtest and live data type mismatch: "
            f"backtest={backtest_coin_type}, live={trading_coin_type}"
        )

    if 'spot' in all_type:
        single_coin_backtest_kline = single_coin_backtest_kline[
            single_coin_backtest_kline['is_spot'] == 1
        ]
        single_coin_trading_kline = single_coin_trading_kline[
            single_coin_trading_kline['is_spot'] == 1
        ]
    elif 'swap' in all_type and 'spot' not in backtest_coin_type | trading_coin_type:
        single_coin_backtest_kline = single_coin_backtest_kline[
            (single_coin_backtest_kline['is_spot'] == 0) &
            (single_coin_backtest_kline['symbol_swap'] != '')
        ]
        single_coin_trading_kline = single_coin_trading_kline[
            single_coin_trading_kline['is_spot'] == 0
        ]

    # 整理数据
    col_rename = ['close'] + factors_name_list
    single_coin_backtest_kline = single_coin_backtest_kline[
        ['candle_begin_time', 'close'] + factors_name_list
    ]
    single_coin_backtest_kline = single_coin_backtest_kline.rename(
        columns={x: f"backtest_{x}(right)" if x != 'close' else f"backtest_{x}(left)" for x in col_rename}
    )

    single_coin_trading_kline = single_coin_trading_kline[
        ['candle_begin_time', 'close'] + factors_name_list
    ]
    single_coin_trading_kline = single_coin_trading_kline.rename(
        columns={x: f"live_{x}(right)" if x != 'close' else f"live_{x}(left)" for x in col_rename}
    )

    merged_factors = pd.merge(
        single_coin_backtest_kline,
        single_coin_trading_kline,
        how='inner',
        on='candle_begin_time'
    )
    merged_factors.set_index('candle_begin_time', inplace=True)

    return merged_factors
