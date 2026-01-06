"""
配置包

包含项目的各类配置文件。
"""

# 导出回测配置变量，供 strategy_hub/core 使用
from config.backtest_config import (
    backtest_path,
    backtest_iter_path,
    backtest_name,
    pre_data_path,
    raw_data_path,
    spot_path,
    swap_path,
    data_source_dict,
    start_date,
    end_date,
    strategy_list,
    min_kline_num,
    black_list,
    white_list,
    account_type,
    initial_usdt,
    leverage,
    margin_rate,
    swap_c_rate,
    spot_c_rate,
    swap_min_order_limit,
    spot_min_order_limit,
    avg_price_col,
    job_num,
    factor_col_limit,
    stable_symbol,
)
