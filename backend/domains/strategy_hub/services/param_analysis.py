"""
参数分析服务

分析参数遍历结果，生成热力图和平原图。
"""

import itertools
import logging
import operator
from dataclasses import dataclass, field
from functools import reduce
from pathlib import Path
from typing import Dict, List, Any, Optional, Literal

import pandas as pd

from domains.mcp_core.paths import get_data_dir
from ..utils.plot_functions import (
    draw_params_bar_plotly,
    draw_params_heatmap_plotly,
    draw_bar_plotly,
    merge_html_flexible,
)

logger = logging.getLogger(__name__)


@dataclass
class ParamAnalysisResult:
    """参数分析结果"""
    name: str
    analysis_type: str  # 'single' or 'double'
    indicator: str
    html_path: Optional[str] = None
    error: Optional[str] = None


class ParamAnalysisService:
    """
    参数分析服务

    分析参数遍历结果，支持单参数平原图和双参数热力图。
    """

    SUPPORTED_INDICATORS = [
        "cumulative_nav",
        "annual_return",
        "max_drawdown",
        "return_drawdown_ratio",
        "win_periods",
        "loss_periods",
        "win_rate",
        "avg_period_return",
        "profit_loss_ratio",
        "max_period_profit",
        "max_period_loss",
        "max_consecutive_wins",
        "max_consecutive_losses",
        "return_std",
    ]

    def __init__(self, data_path: Optional[Path] = None):
        """
        初始化服务

        Args:
            data_path: 数据根路径
        """
        self.data_path = data_path or get_data_dir()
        self.traversal_path = self.data_path / "traversal_results"
        self.output_path = self.data_path / "analysis_results" / "param_analysis"
        self.output_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _generate_param_combinations(batch_params: Dict[str, List[Any]]) -> pd.DataFrame:
        """
        生成参数组合DataFrame

        Args:
            batch_params: 参数字典

        Returns:
            参数组合DataFrame
        """
        keys = list(batch_params.keys())
        values = list(batch_params.values())
        combinations = [dict(zip(keys, combo)) for combo in itertools.product(*values)]
        df = pd.DataFrame(combinations)
        df["param_combo"] = [f"param_combo_{i + 1}" for i in range(len(df))]
        return df

    @staticmethod
    def _filter_dataframe(
        df: pd.DataFrame,
        filter_dict: Dict[str, List[Any]]
    ) -> pd.DataFrame:
        """
        按条件过滤DataFrame

        Args:
            df: 数据DataFrame
            filter_dict: 过滤条件 {列名: [值列表]}

        Returns:
            过滤后的DataFrame
        """
        if not filter_dict:
            return df.copy()
        conditions = [df[col].isin(values) for col, values in filter_dict.items()]
        return df[reduce(operator.and_, conditions)] if conditions else df.copy()

    def _load_evaluation_data(
        self,
        df: pd.DataFrame,
        result_dir: Path,
        indicator: str
    ) -> Optional[List[str]]:
        """
        加载策略评价数据

        Args:
            df: 参数组合DataFrame
            result_dir: 结果目录
            indicator: 评价指标

        Returns:
            时间列表(用于年化收益)或None
        """
        if indicator == "annual_return":
            time_list = []
            for folder in df["param_combo"]:
                stats_path = result_dir / folder / "strategy_evaluation.csv"
                stats = pd.read_csv(stats_path, encoding="utf-8")
                stats.columns = ["indicator", "value"]
                if stats.empty:
                    raise ValueError(f"{folder} evaluation data is empty")
                stats = stats.set_index("indicator")
                df.loc[df["param_combo"] == folder, "all"] = stats.loc[indicator, "value"]

                years_path = result_dir / folder / "annual_return.csv"
                years = pd.read_csv(years_path, encoding="utf-8")
                if years.empty:
                    raise ValueError(f"{folder} annual return data is empty")
                time_list = list(years["candle_begin_time"].sort_values(ascending=False))
                for time in time_list:
                    df.loc[df["param_combo"] == folder, time] = years.loc[
                        years["candle_begin_time"] == time, "change_pct"
                    ].iloc[0]

            # 转换百分比格式
            df[["all"] + time_list] = df[["all"] + time_list].applymap(
                lambda x: float(x.replace("%", "")) / 100 if "%" in str(x) else float(x)
            )
            return time_list
        else:
            for folder in df["param_combo"]:
                stats_path = result_dir / folder / "strategy_evaluation.csv"
                stats = pd.read_csv(stats_path, encoding="utf-8")
                if stats.empty:
                    raise ValueError(f"{folder} evaluation data is empty")
                stats.columns = ["indicator", "value"]
                stats = stats.set_index("indicator")
                df.loc[df["param_combo"] == folder, indicator] = stats.loc[indicator, "value"]

            df[indicator] = df[indicator].apply(
                lambda x: float(x.replace("%", "")) / 100 if "%" in str(x) else float(x)
            )
            return None

    def analyze_single_param(
        self,
        trav_name: str,
        batch_params: Dict[str, List[Any]],
        param_x: str,
        limit_dict: Optional[Dict[str, List[Any]]] = None,
        indicator: str = "annual_return"
    ) -> ParamAnalysisResult:
        """
        单参数平原图分析

        Args:
            trav_name: 遍历结果名称
            batch_params: 参数范围
            param_x: X轴参数
            limit_dict: 固定参数条件
            indicator: 评价指标

        Returns:
            分析结果
        """
        result = ParamAnalysisResult(
            name=trav_name,
            analysis_type="single",
            indicator=indicator
        )

        try:
            result_dir = self.traversal_path / trav_name
            output_dir = self.output_path / "plain_chart" / trav_name
            output_dir.mkdir(parents=True, exist_ok=True)

            df = self._generate_param_combinations(batch_params)
            df = self._filter_dataframe(df, limit_dict or {})

            time_list = self._load_evaluation_data(df, result_dir, indicator)

            # 排序处理
            if "hold_period" in df.columns:
                df["periods"] = df["hold_period"].apply(lambda x: int(x[:-1]))
                df = df.sort_values(by=["periods"])

            fig_list = []
            if indicator == "annual_return":
                sub_df = df[[param_x] + ["all"] + time_list].copy()
                sub_df[param_x] = sub_df[param_x].map(lambda x: f"{param_x}_{x}")
                sub_df = sub_df.set_index(param_x)
                fig = draw_params_bar_plotly(sub_df, indicator)
            else:
                x_axis = df[param_x].map(lambda x: f"{param_x}_{x}")
                fig = draw_bar_plotly(
                    x_axis, df[indicator], title=indicator, pic_size=[1800, 600]
                )
            fig_list.append(fig)

            html_name = f"{param_x}_{indicator}.html"
            html_path = output_dir / html_name
            merge_html_flexible(fig_list, html_path, title="Parameter Plain Chart", show=False)

            result.html_path = str(html_path)
            logger.info(f"Single param analysis completed: {trav_name}")

        except Exception as e:
            logger.error(f"Single param analysis failed: {e}")
            result.error = str(e)

        return result

    def analyze_double_params(
        self,
        trav_name: str,
        batch_params: Dict[str, List[Any]],
        param_x: str,
        param_y: str,
        limit_dict: Optional[Dict[str, List[Any]]] = None,
        indicator: str = "annual_return"
    ) -> ParamAnalysisResult:
        """
        双参数热力图分析

        Args:
            trav_name: 遍历结果名称
            batch_params: 参数范围
            param_x: X轴参数
            param_y: Y轴参数
            limit_dict: 固定参数条件
            indicator: 评价指标

        Returns:
            分析结果
        """
        result = ParamAnalysisResult(
            name=trav_name,
            analysis_type="double",
            indicator=indicator
        )

        try:
            result_dir = self.traversal_path / trav_name
            output_dir = self.output_path / "heatmap" / trav_name
            output_dir.mkdir(parents=True, exist_ok=True)

            df = self._generate_param_combinations(batch_params)
            df = self._filter_dataframe(df, limit_dict or {})

            time_list = self._load_evaluation_data(df, result_dir, indicator)

            # 排序处理
            if "hold_period" in df.columns:
                df["periods"] = df["hold_period"].apply(lambda x: int(x[:-1]))
                df = df.sort_values(by=["periods"])

            fig_list = []
            if indicator == "annual_return":
                for time in ["all"] + (time_list or []):
                    temp = pd.pivot_table(df, index=param_y, columns=param_x, values=time)
                    fig = draw_params_heatmap_plotly(temp, title=time)
                    fig_list.append(fig)
            else:
                temp = pd.pivot_table(df, index=param_y, columns=param_x, values=indicator)
                fig = draw_params_heatmap_plotly(temp, title=indicator)
                fig_list.append(fig)

            html_name = f"{param_x}_{param_y}_{indicator}.html"
            html_path = output_dir / html_name
            merge_html_flexible(fig_list, html_path, title="Parameter Heatmap", show=False)

            result.html_path = str(html_path)
            logger.info(f"Double param analysis completed: {trav_name}")

        except Exception as e:
            logger.error(f"Double param analysis failed: {e}")
            result.error = str(e)

        return result

    def analyze(
        self,
        trav_name: str,
        batch_params: Dict[str, List[Any]],
        param_x: str,
        param_y: Optional[str] = None,
        limit_dict: Optional[Dict[str, List[Any]]] = None,
        indicator: str = "annual_return"
    ) -> ParamAnalysisResult:
        """
        参数分析（自动选择单参数或双参数分析）

        Args:
            trav_name: 遍历结果名称
            batch_params: 参数范围
            param_x: X轴参数
            param_y: Y轴参数（可选，为空则单参数分析）
            limit_dict: 固定参数条件
            indicator: 评价指标

        Returns:
            分析结果
        """
        if param_y:
            return self.analyze_double_params(
                trav_name, batch_params, param_x, param_y, limit_dict, indicator
            )
        else:
            return self.analyze_single_param(
                trav_name, batch_params, param_x, limit_dict, indicator
            )


# 单例模式
_param_analysis_service: Optional[ParamAnalysisService] = None


def get_param_analysis_service() -> ParamAnalysisService:
    """获取参数分析服务单例"""
    global _param_analysis_service
    if _param_analysis_service is None:
        _param_analysis_service = ParamAnalysisService()
    return _param_analysis_service


def reset_param_analysis_service() -> None:
    """重置服务单例"""
    global _param_analysis_service
    _param_analysis_service = None
