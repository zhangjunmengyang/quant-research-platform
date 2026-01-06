"""
策略知识库工具函数模块

包含绘图和数据处理工具函数。
"""

from .plot_functions import (
    float_num_process,
    merge_html_flexible,
    draw_params_bar_plotly,
    draw_params_heatmap_plotly,
    draw_bar_plotly,
    draw_line_plotly,
    draw_coins_difference,
    draw_equity_curve_plotly,
    draw_coins_table,
)

from .data_functions import (
    group_analysis,
    coins_difference_all_pairs,
    curve_difference_all_pairs,
    process_equity_data,
    process_coin_selection_data,
    process_backtest_trading_factors,
)

__all__ = [
    # 绘图函数
    'float_num_process',
    'merge_html_flexible',
    'draw_params_bar_plotly',
    'draw_params_heatmap_plotly',
    'draw_bar_plotly',
    'draw_line_plotly',
    'draw_coins_difference',
    'draw_equity_curve_plotly',
    'draw_coins_table',
    # 数据处理函数
    'group_analysis',
    'coins_difference_all_pairs',
    'curve_difference_all_pairs',
    'process_equity_data',
    'process_coin_selection_data',
    'process_backtest_trading_factors',
]
