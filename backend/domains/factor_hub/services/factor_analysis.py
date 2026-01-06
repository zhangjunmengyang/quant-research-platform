"""
因子分析服务

提供单因子分析能力，包括：
- IC 分析（IC均值、ICIR、IC衰减）
- 分组收益分析
- 因子分布分析
- 因子稳定性分析
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class ICAnalysisResult:
    """IC分析结果"""
    ic_mean: float = 0.0  # IC均值
    ic_std: float = 0.0  # IC标准差
    icir: float = 0.0  # ICIR (IC均值/IC标准差)
    ic_positive_ratio: float = 0.0  # IC为正的比例
    ic_series: Optional[pd.Series] = None  # IC时序数据
    rank_ic_mean: float = 0.0  # RankIC均值
    rank_ic_std: float = 0.0  # RankIC标准差
    rank_icir: float = 0.0  # RankICIR

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ic_mean": round(self.ic_mean, 4),
            "ic_std": round(self.ic_std, 4),
            "icir": round(self.icir, 4),
            "ic_positive_ratio": round(self.ic_positive_ratio, 4),
            "rank_ic_mean": round(self.rank_ic_mean, 4),
            "rank_ic_std": round(self.rank_ic_std, 4),
            "rank_icir": round(self.rank_icir, 4),
        }


@dataclass
class GroupReturnResult:
    """分组收益分析结果"""
    group_returns: Dict[int, float] = field(default_factory=dict)  # 各组平均收益
    long_short_return: float = 0.0  # 多空收益
    monotonicity: float = 0.0  # 单调性（相邻组收益差异一致性）
    group_cumulative: Optional[pd.DataFrame] = None  # 分组累计收益

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_returns": {k: round(v, 4) for k, v in self.group_returns.items()},
            "long_short_return": round(self.long_short_return, 4),
            "monotonicity": round(self.monotonicity, 4),
        }


@dataclass
class DistributionResult:
    """分布分析结果"""
    mean: float = 0.0
    std: float = 0.0
    skewness: float = 0.0  # 偏度
    kurtosis: float = 0.0  # 峰度
    min_val: float = 0.0
    max_val: float = 0.0
    percentiles: Dict[str, float] = field(default_factory=dict)
    normality_test: Tuple[float, float] = (0.0, 0.0)  # (统计量, p值)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mean": round(self.mean, 4),
            "std": round(self.std, 4),
            "skewness": round(self.skewness, 4),
            "kurtosis": round(self.kurtosis, 4),
            "min": round(self.min_val, 4),
            "max": round(self.max_val, 4),
            "percentiles": {k: round(v, 4) for k, v in self.percentiles.items()},
            "normality_p_value": round(self.normality_test[1], 4),
        }


@dataclass
class StabilityResult:
    """稳定性分析结果"""
    rolling_ic_mean: float = 0.0  # 滚动IC均值的均值
    rolling_ic_std: float = 0.0  # 滚动IC均值的标准差
    ic_decay: List[float] = field(default_factory=list)  # IC衰减序列
    half_life: int = 0  # 半衰期（IC衰减到0.5倍所需周期数）
    autocorr: float = 0.0  # 自相关系数

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rolling_ic_mean": round(self.rolling_ic_mean, 4),
            "rolling_ic_std": round(self.rolling_ic_std, 4),
            "ic_decay": [round(x, 4) for x in self.ic_decay[:10]],  # 只返回前10期
            "half_life": self.half_life,
            "autocorr": round(self.autocorr, 4),
        }


@dataclass
class FactorAnalysisResult:
    """完整的因子分析结果"""
    factor_name: str
    param: Any
    analysis_date: str = field(default_factory=lambda: datetime.now().isoformat())
    ic_analysis: Optional[ICAnalysisResult] = None
    group_return: Optional[GroupReturnResult] = None
    distribution: Optional[DistributionResult] = None
    stability: Optional[StabilityResult] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "factor_name": self.factor_name,
            "param": self.param,
            "analysis_date": self.analysis_date,
        }
        if self.ic_analysis:
            result["ic_analysis"] = self.ic_analysis.to_dict()
        if self.group_return:
            result["group_return"] = self.group_return.to_dict()
        if self.distribution:
            result["distribution"] = self.distribution.to_dict()
        if self.stability:
            result["stability"] = self.stability.to_dict()
        return result


class FactorAnalysisService:
    """
    因子分析服务

    提供单因子分析的各种功能。
    """

    def __init__(self, n_groups: int = 5):
        """
        初始化分析服务

        Args:
            n_groups: 分组数量，默认5组
        """
        self.n_groups = n_groups

    def analyze(
        self,
        factor_df: pd.DataFrame,
        factor_col: str,
        return_col: str = "next_return",
        time_col: str = "candle_begin_time",
        symbol_col: str = "symbol",
    ) -> FactorAnalysisResult:
        """
        执行完整的因子分析

        Args:
            factor_df: 包含因子值和收益的DataFrame
            factor_col: 因子列名
            return_col: 收益列名
            time_col: 时间列名
            symbol_col: 标的列名

        Returns:
            FactorAnalysisResult
        """
        # 提取因子名称和参数
        parts = factor_col.rsplit("_", 1)
        factor_name = parts[0] if len(parts) > 1 else factor_col
        param = parts[1] if len(parts) > 1 else ""

        result = FactorAnalysisResult(
            factor_name=factor_name,
            param=param,
        )

        # 数据预处理
        df = factor_df[[time_col, symbol_col, factor_col, return_col]].dropna()

        if df.empty:
            logger.warning(f"因子 {factor_col} 无有效数据")
            return result

        # IC分析
        try:
            result.ic_analysis = self.calculate_ic(df, factor_col, return_col, time_col)
        except Exception as e:
            logger.warning(f"IC分析失败: {e}")

        # 分组收益分析
        try:
            result.group_return = self.calculate_group_return(
                df, factor_col, return_col, time_col
            )
        except Exception as e:
            logger.warning(f"分组收益分析失败: {e}")

        # 分布分析
        try:
            result.distribution = self.calculate_distribution(df, factor_col)
        except Exception as e:
            logger.warning(f"分布分析失败: {e}")

        # 稳定性分析
        try:
            result.stability = self.calculate_stability(
                df, factor_col, return_col, time_col
            )
        except Exception as e:
            logger.warning(f"稳定性分析失败: {e}")

        return result

    def calculate_ic(
        self,
        df: pd.DataFrame,
        factor_col: str,
        return_col: str,
        time_col: str,
    ) -> ICAnalysisResult:
        """
        计算IC（信息系数）

        IC = corr(因子值, 下期收益)

        Args:
            df: 数据DataFrame
            factor_col: 因子列名
            return_col: 收益列名
            time_col: 时间列名

        Returns:
            ICAnalysisResult
        """
        result = ICAnalysisResult()

        # 按时间分组计算IC
        ic_list = []
        rank_ic_list = []

        for _, group in df.groupby(time_col):
            if len(group) < 10:  # 样本太少跳过
                continue

            factor_vals = group[factor_col].values
            return_vals = group[return_col].values

            # Pearson IC
            ic = np.corrcoef(factor_vals, return_vals)[0, 1]
            if not np.isnan(ic):
                ic_list.append(ic)

            # Spearman Rank IC
            rank_ic = stats.spearmanr(factor_vals, return_vals)[0]
            if not np.isnan(rank_ic):
                rank_ic_list.append(rank_ic)

        if ic_list:
            ic_series = pd.Series(ic_list)
            result.ic_series = ic_series
            result.ic_mean = ic_series.mean()
            result.ic_std = ic_series.std()
            result.icir = result.ic_mean / result.ic_std if result.ic_std > 0 else 0
            result.ic_positive_ratio = (ic_series > 0).mean()

        if rank_ic_list:
            rank_ic_series = pd.Series(rank_ic_list)
            result.rank_ic_mean = rank_ic_series.mean()
            result.rank_ic_std = rank_ic_series.std()
            result.rank_icir = (
                result.rank_ic_mean / result.rank_ic_std
                if result.rank_ic_std > 0
                else 0
            )

        return result

    def calculate_group_return(
        self,
        df: pd.DataFrame,
        factor_col: str,
        return_col: str,
        time_col: str,
    ) -> GroupReturnResult:
        """
        计算分组收益

        按因子值将股票分成N组，计算各组平均收益。

        Args:
            df: 数据DataFrame
            factor_col: 因子列名
            return_col: 收益列名
            time_col: 时间列名

        Returns:
            GroupReturnResult
        """
        result = GroupReturnResult()

        # 按时间分组，在每个截面上进行分组
        group_returns_all = {i: [] for i in range(self.n_groups)}

        for _, group in df.groupby(time_col):
            if len(group) < self.n_groups * 2:  # 样本太少跳过
                continue

            # 按因子值分组
            group = group.copy()
            group["_group"] = pd.qcut(
                group[factor_col],
                self.n_groups,
                labels=False,
                duplicates="drop",
            )

            # 计算各组平均收益
            for g in range(self.n_groups):
                g_ret = group[group["_group"] == g][return_col].mean()
                if not np.isnan(g_ret):
                    group_returns_all[g].append(g_ret)

        # 计算平均收益
        for g in range(self.n_groups):
            if group_returns_all[g]:
                result.group_returns[g] = np.mean(group_returns_all[g])

        # 多空收益
        if 0 in result.group_returns and (self.n_groups - 1) in result.group_returns:
            result.long_short_return = (
                result.group_returns[self.n_groups - 1] - result.group_returns[0]
            )

        # 单调性检验
        if len(result.group_returns) >= 3:
            returns = [result.group_returns.get(i, 0) for i in range(self.n_groups)]
            diffs = [returns[i + 1] - returns[i] for i in range(len(returns) - 1)]
            if diffs:
                # 计算差值符号一致性
                signs = [1 if d > 0 else -1 if d < 0 else 0 for d in diffs]
                result.monotonicity = abs(sum(signs)) / len(signs)

        return result

    def calculate_distribution(
        self,
        df: pd.DataFrame,
        factor_col: str,
    ) -> DistributionResult:
        """
        计算因子分布特征

        Args:
            df: 数据DataFrame
            factor_col: 因子列名

        Returns:
            DistributionResult
        """
        result = DistributionResult()

        factor_vals = df[factor_col].dropna().values

        if len(factor_vals) < 10:
            return result

        result.mean = np.mean(factor_vals)
        result.std = np.std(factor_vals)
        result.skewness = stats.skew(factor_vals)
        result.kurtosis = stats.kurtosis(factor_vals)
        result.min_val = np.min(factor_vals)
        result.max_val = np.max(factor_vals)

        # 分位数
        for p in [1, 5, 25, 50, 75, 95, 99]:
            result.percentiles[f"p{p}"] = np.percentile(factor_vals, p)

        # 正态性检验（样本量限制）
        if len(factor_vals) <= 5000:
            try:
                result.normality_test = stats.shapiro(factor_vals[:5000])
            except Exception:
                pass

        return result

    def calculate_stability(
        self,
        df: pd.DataFrame,
        factor_col: str,
        return_col: str,
        time_col: str,
        window: int = 20,
        max_lag: int = 10,
    ) -> StabilityResult:
        """
        计算因子稳定性

        Args:
            df: 数据DataFrame
            factor_col: 因子列名
            return_col: 收益列名
            time_col: 时间列名
            window: 滚动窗口大小
            max_lag: 最大滞后期数

        Returns:
            StabilityResult
        """
        result = StabilityResult()

        # 先计算IC序列
        ic_analysis = self.calculate_ic(df, factor_col, return_col, time_col)
        if ic_analysis.ic_series is None or len(ic_analysis.ic_series) < window:
            return result

        ic_series = ic_analysis.ic_series

        # 滚动IC分析
        rolling_ic = ic_series.rolling(window=window).mean()
        result.rolling_ic_mean = rolling_ic.mean()
        result.rolling_ic_std = rolling_ic.std()

        # IC衰减分析（计算滞后收益与当期因子的相关性）
        times = df[time_col].unique()
        times = sorted(times)

        if len(times) > max_lag + 1:
            decay_list = []
            for lag in range(1, max_lag + 1):
                lag_ic_list = []
                for i in range(lag, len(times)):
                    current_time = times[i - lag]
                    future_time = times[i]

                    current_df = df[df[time_col] == current_time]
                    future_df = df[df[time_col] == future_time]

                    if len(current_df) < 10 or len(future_df) < 10:
                        continue

                    # 合并计算滞后IC
                    merged = current_df.merge(
                        future_df[["symbol", return_col]].rename(
                            columns={return_col: "future_return"}
                        ),
                        on="symbol",
                    )
                    if len(merged) >= 10:
                        lag_ic = np.corrcoef(
                            merged[factor_col].values, merged["future_return"].values
                        )[0, 1]
                        if not np.isnan(lag_ic):
                            lag_ic_list.append(lag_ic)

                if lag_ic_list:
                    decay_list.append(np.mean(lag_ic_list))

            result.ic_decay = decay_list

            # 计算半衰期
            if decay_list and decay_list[0] != 0:
                initial_ic = abs(decay_list[0])
                for i, ic in enumerate(decay_list):
                    if abs(ic) < initial_ic * 0.5:
                        result.half_life = i + 1
                        break
                else:
                    result.half_life = len(decay_list)

        # 因子自相关
        if len(ic_series) >= 2:
            result.autocorr = ic_series.autocorr(lag=1)

        return result

    def quick_analyze(
        self,
        factor_df: pd.DataFrame,
        factor_col: str,
        return_col: str = "next_return",
        time_col: str = "candle_begin_time",
    ) -> Dict[str, Any]:
        """
        快速分析（只返回核心指标）

        Args:
            factor_df: 数据DataFrame
            factor_col: 因子列名
            return_col: 收益列名
            time_col: 时间列名

        Returns:
            核心指标字典
        """
        result = self.analyze(factor_df, factor_col, return_col, time_col)
        summary = {
            "factor_name": result.factor_name,
            "param": result.param,
        }

        if result.ic_analysis:
            summary["ic_mean"] = round(result.ic_analysis.ic_mean, 4)
            summary["icir"] = round(result.ic_analysis.icir, 4)
            summary["rank_ic_mean"] = round(result.ic_analysis.rank_ic_mean, 4)

        if result.group_return:
            summary["long_short_return"] = round(result.group_return.long_short_return, 4)
            summary["monotonicity"] = round(result.group_return.monotonicity, 4)

        if result.stability:
            summary["half_life"] = result.stability.half_life

        return summary


# 单例实例
_factor_analysis_service: Optional[FactorAnalysisService] = None


def get_factor_analysis_service(n_groups: int = 5) -> FactorAnalysisService:
    """获取因子分析服务单例"""
    global _factor_analysis_service
    if _factor_analysis_service is None:
        _factor_analysis_service = FactorAnalysisService(n_groups=n_groups)
    return _factor_analysis_service
