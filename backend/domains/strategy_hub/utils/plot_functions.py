"""
绘图工具函数模块

此模块从 engine.chart_utils 重新导出绘图函数，保持后向兼容性。
所有绘图函数的实现已迁移到 domains.engine.chart_utils。
"""

from domains.engine.chart_utils import (
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

# 内部辅助函数也从 engine 导入（用于测试或扩展）
from domains.engine.chart_utils import (
    _open_in_browser,
    _save_and_show,
)

__all__ = [
    "float_num_process",
    "merge_html_flexible",
    "draw_params_bar_plotly",
    "draw_params_heatmap_plotly",
    "draw_bar_plotly",
    "draw_line_plotly",
    "draw_coins_difference",
    "draw_equity_curve_plotly",
    "draw_coins_table",
]
