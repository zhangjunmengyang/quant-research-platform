"""
多因子分析服务

提供多因子分析能力，包括：
- 因子相关性矩阵计算
- 因子共线性检测
- 因子正交化
- 因子合成（等权、IC加权、优化权重）
- 因子冗余检测
- 因子增量贡献分析
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import numpy as np
import pandas as pd
from scipy import stats
from scipy.linalg import qr

logger = logging.getLogger(__name__)


class SynthesisMethod(str, Enum):
    """因子合成方法"""
    EQUAL_WEIGHT = "equal_weight"  # 等权
    IC_WEIGHT = "ic_weight"  # IC加权
    ICIR_WEIGHT = "icir_weight"  # ICIR加权
    MAX_IC = "max_ic"  # 最大化IC
    MIN_CORR = "min_corr"  # 最小化相关性


@dataclass
class CorrelationMatrixResult:
    """因子相关性矩阵结果"""
    correlation_matrix: pd.DataFrame = None  # 相关性矩阵
    rank_correlation_matrix: pd.DataFrame = None  # 秩相关性矩阵
    factor_names: List[str] = field(default_factory=list)
    high_corr_pairs: List[Tuple[str, str, float]] = field(default_factory=list)  # 高相关因子对
    avg_correlation: float = 0.0  # 平均相关性
    max_correlation: float = 0.0  # 最大相关性

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "factor_names": self.factor_names,
            "high_corr_pairs": [
                {"factor1": p[0], "factor2": p[1], "correlation": round(p[2], 4)}
                for p in self.high_corr_pairs
            ],
            "avg_correlation": round(self.avg_correlation, 4),
            "max_correlation": round(self.max_correlation, 4),
        }
        if self.correlation_matrix is not None:
            result["correlation_matrix"] = self.correlation_matrix.round(4).to_dict()
        return result


@dataclass
class CollinearityResult:
    """共线性检测结果"""
    vif_scores: Dict[str, float] = field(default_factory=dict)  # 方差膨胀因子
    condition_number: float = 0.0  # 条件数
    collinear_factors: List[str] = field(default_factory=list)  # 存在共线性的因子
    eigenvalues: List[float] = field(default_factory=list)  # 特征值
    is_multicollinear: bool = False  # 是否存在严重共线性

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vif_scores": {k: round(v, 4) for k, v in self.vif_scores.items()},
            "condition_number": round(self.condition_number, 4),
            "collinear_factors": self.collinear_factors,
            "eigenvalues": [round(e, 4) for e in self.eigenvalues[:10]],
            "is_multicollinear": self.is_multicollinear,
        }


@dataclass
class OrthogonalizationResult:
    """因子正交化结果"""
    orthogonal_factors: pd.DataFrame = None  # 正交化后的因子
    factor_names: List[str] = field(default_factory=list)
    residual_ic: Dict[str, float] = field(default_factory=dict)  # 正交化后的IC
    explained_variance_ratio: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_names": self.factor_names,
            "residual_ic": {k: round(v, 4) for k, v in self.residual_ic.items()},
            "explained_variance_ratio": {
                k: round(v, 4) for k, v in self.explained_variance_ratio.items()
            },
        }


@dataclass
class SynthesisResult:
    """因子合成结果"""
    method: str = ""
    weights: Dict[str, float] = field(default_factory=dict)
    synthetic_factor: pd.Series = None
    synthetic_ic: float = 0.0
    synthetic_icir: float = 0.0
    improvement_ratio: float = 0.0  # 相比单因子的提升比例

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "synthetic_ic": round(self.synthetic_ic, 4),
            "synthetic_icir": round(self.synthetic_icir, 4),
            "improvement_ratio": round(self.improvement_ratio, 4),
        }


@dataclass
class RedundancyResult:
    """因子冗余检测结果"""
    redundant_factors: List[str] = field(default_factory=list)  # 冗余因子
    redundancy_scores: Dict[str, float] = field(default_factory=dict)  # 冗余度评分
    recommended_removal: List[str] = field(default_factory=list)  # 建议移除的因子
    factor_clusters: List[List[str]] = field(default_factory=list)  # 因子聚类

    def to_dict(self) -> Dict[str, Any]:
        return {
            "redundant_factors": self.redundant_factors,
            "redundancy_scores": {k: round(v, 4) for k, v in self.redundancy_scores.items()},
            "recommended_removal": self.recommended_removal,
            "factor_clusters": self.factor_clusters,
        }


@dataclass
class IncrementalContributionResult:
    """因子增量贡献分析结果"""
    marginal_contributions: Dict[str, float] = field(default_factory=dict)  # 边际贡献
    cumulative_contributions: Dict[str, float] = field(default_factory=dict)  # 累计贡献
    contribution_order: List[str] = field(default_factory=list)  # 贡献排序
    total_ic: float = 0.0  # 总IC
    shapley_values: Dict[str, float] = field(default_factory=dict)  # Shapley值

    def to_dict(self) -> Dict[str, Any]:
        return {
            "marginal_contributions": {
                k: round(v, 4) for k, v in self.marginal_contributions.items()
            },
            "cumulative_contributions": {
                k: round(v, 4) for k, v in self.cumulative_contributions.items()
            },
            "contribution_order": self.contribution_order,
            "total_ic": round(self.total_ic, 4),
            "shapley_values": {k: round(v, 4) for k, v in self.shapley_values.items()},
        }


@dataclass
class MultiFactorAnalysisResult:
    """多因子分析完整结果"""
    factor_names: List[str] = field(default_factory=list)
    analysis_date: str = field(default_factory=lambda: datetime.now().isoformat())
    correlation: Optional[CorrelationMatrixResult] = None
    collinearity: Optional[CollinearityResult] = None
    orthogonalization: Optional[OrthogonalizationResult] = None
    synthesis: Optional[SynthesisResult] = None
    redundancy: Optional[RedundancyResult] = None
    incremental_contribution: Optional[IncrementalContributionResult] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "factor_names": self.factor_names,
            "analysis_date": self.analysis_date,
        }
        if self.correlation:
            result["correlation"] = self.correlation.to_dict()
        if self.collinearity:
            result["collinearity"] = self.collinearity.to_dict()
        if self.orthogonalization:
            result["orthogonalization"] = self.orthogonalization.to_dict()
        if self.synthesis:
            result["synthesis"] = self.synthesis.to_dict()
        if self.redundancy:
            result["redundancy"] = self.redundancy.to_dict()
        if self.incremental_contribution:
            result["incremental_contribution"] = self.incremental_contribution.to_dict()
        return result


class MultiFactorAnalysisService:
    """
    多因子分析服务

    提供多因子分析的各种功能。
    """

    def __init__(
        self,
        correlation_threshold: float = 0.7,
        vif_threshold: float = 10.0,
    ):
        """
        初始化多因子分析服务

        Args:
            correlation_threshold: 高相关性阈值
            vif_threshold: VIF阈值（超过此值认为存在共线性）
        """
        self.correlation_threshold = correlation_threshold
        self.vif_threshold = vif_threshold

    def analyze(
        self,
        factor_df: pd.DataFrame,
        factor_cols: List[str],
        return_col: str = "next_return",
        time_col: str = "candle_begin_time",
        symbol_col: str = "symbol",
        synthesis_method: SynthesisMethod = SynthesisMethod.IC_WEIGHT,
    ) -> MultiFactorAnalysisResult:
        """
        执行完整的多因子分析

        Args:
            factor_df: 包含多个因子值和收益的DataFrame
            factor_cols: 因子列名列表
            return_col: 收益列名
            time_col: 时间列名
            symbol_col: 标的列名
            synthesis_method: 因子合成方法

        Returns:
            MultiFactorAnalysisResult
        """
        result = MultiFactorAnalysisResult(factor_names=factor_cols)

        # 数据预处理
        cols = [time_col, symbol_col] + factor_cols + [return_col]
        df = factor_df[cols].dropna()

        if df.empty or len(factor_cols) < 2:
            logger.warning("无足够数据或因子数量不足")
            return result

        # 相关性分析
        try:
            result.correlation = self.calculate_correlation_matrix(df, factor_cols)
        except Exception as e:
            logger.warning(f"相关性分析失败: {e}")

        # 共线性检测
        try:
            result.collinearity = self.detect_collinearity(df, factor_cols)
        except Exception as e:
            logger.warning(f"共线性检测失败: {e}")

        # 正交化
        try:
            result.orthogonalization = self.orthogonalize_factors(
                df, factor_cols, return_col, time_col
            )
        except Exception as e:
            logger.warning(f"正交化失败: {e}")

        # 因子合成
        try:
            result.synthesis = self.synthesize_factors(
                df, factor_cols, return_col, time_col, synthesis_method
            )
        except Exception as e:
            logger.warning(f"因子合成失败: {e}")

        # 冗余检测
        try:
            result.redundancy = self.detect_redundancy(
                df, factor_cols, return_col, time_col
            )
        except Exception as e:
            logger.warning(f"冗余检测失败: {e}")

        # 增量贡献分析
        try:
            result.incremental_contribution = self.analyze_incremental_contribution(
                df, factor_cols, return_col, time_col
            )
        except Exception as e:
            logger.warning(f"增量贡献分析失败: {e}")

        return result

    def calculate_correlation_matrix(
        self,
        df: pd.DataFrame,
        factor_cols: List[str],
    ) -> CorrelationMatrixResult:
        """
        计算因子相关性矩阵

        Args:
            df: 数据DataFrame
            factor_cols: 因子列名列表

        Returns:
            CorrelationMatrixResult
        """
        result = CorrelationMatrixResult(factor_names=factor_cols)

        factor_data = df[factor_cols]

        # Pearson相关性
        result.correlation_matrix = factor_data.corr(method="pearson")

        # Spearman秩相关性
        result.rank_correlation_matrix = factor_data.corr(method="spearman")

        # 计算高相关因子对
        corr_matrix = result.correlation_matrix.values
        n = len(factor_cols)
        corr_values = []

        for i in range(n):
            for j in range(i + 1, n):
                corr = abs(corr_matrix[i, j])
                corr_values.append(corr)
                if corr > self.correlation_threshold:
                    result.high_corr_pairs.append(
                        (factor_cols[i], factor_cols[j], corr_matrix[i, j])
                    )

        # 按相关性排序
        result.high_corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        if corr_values:
            result.avg_correlation = np.mean(corr_values)
            result.max_correlation = np.max(corr_values)

        return result

    def detect_collinearity(
        self,
        df: pd.DataFrame,
        factor_cols: List[str],
    ) -> CollinearityResult:
        """
        检测因子共线性

        使用VIF（方差膨胀因子）和条件数来检测共线性。

        Args:
            df: 数据DataFrame
            factor_cols: 因子列名列表

        Returns:
            CollinearityResult
        """
        result = CollinearityResult()

        factor_data = df[factor_cols].values

        # 标准化
        factor_data = (factor_data - factor_data.mean(axis=0)) / (factor_data.std(axis=0) + 1e-10)

        # 计算VIF
        for i, col in enumerate(factor_cols):
            # 用其他因子回归当前因子
            y = factor_data[:, i]
            X = np.delete(factor_data, i, axis=1)

            if X.shape[1] > 0:
                # 添加常数项
                X = np.column_stack([np.ones(X.shape[0]), X])
                try:
                    # 最小二乘回归
                    coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
                    y_pred = X @ coeffs
                    ss_res = np.sum((y - y_pred) ** 2)
                    ss_tot = np.sum((y - y.mean()) ** 2)
                    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

                    vif = 1 / (1 - r_squared) if r_squared < 1 else float("inf")
                    result.vif_scores[col] = vif

                    if vif > self.vif_threshold:
                        result.collinear_factors.append(col)
                except Exception:
                    result.vif_scores[col] = float("nan")

        # 计算条件数
        try:
            cov_matrix = np.cov(factor_data.T)
            eigenvalues = np.linalg.eigvalsh(cov_matrix)
            eigenvalues = np.sort(eigenvalues)[::-1]
            result.eigenvalues = eigenvalues.tolist()

            # 条件数 = 最大特征值/最小特征值
            if eigenvalues[-1] > 0:
                result.condition_number = eigenvalues[0] / eigenvalues[-1]
            else:
                result.condition_number = float("inf")

        except Exception as e:
            logger.warning(f"计算条件数失败: {e}")

        # 判断是否存在严重共线性
        result.is_multicollinear = (
            len(result.collinear_factors) > 0 or result.condition_number > 30
        )

        return result

    def orthogonalize_factors(
        self,
        df: pd.DataFrame,
        factor_cols: List[str],
        return_col: str,
        time_col: str,
    ) -> OrthogonalizationResult:
        """
        因子正交化

        使用Gram-Schmidt正交化或对称正交化。

        Args:
            df: 数据DataFrame
            factor_cols: 因子列名列表
            return_col: 收益列名
            time_col: 时间列名

        Returns:
            OrthogonalizationResult
        """
        result = OrthogonalizationResult(factor_names=factor_cols)

        factor_data = df[factor_cols].values

        # 标准化
        factor_data = (factor_data - factor_data.mean(axis=0)) / (factor_data.std(axis=0) + 1e-10)

        # 使用QR分解进行正交化
        Q, R = qr(factor_data, mode="economic")

        result.orthogonal_factors = pd.DataFrame(
            Q, columns=[f"{col}_orth" for col in factor_cols], index=df.index
        )

        # 计算正交化后因子的IC
        for i, col in enumerate(factor_cols):
            ic_list = []
            for _, group in df.groupby(time_col):
                if len(group) < 10:
                    continue
                idx = group.index
                if len(set(idx) & set(result.orthogonal_factors.index)) == len(idx):
                    orth_vals = result.orthogonal_factors.loc[idx, f"{col}_orth"].values
                    return_vals = group[return_col].values
                    ic = np.corrcoef(orth_vals, return_vals)[0, 1]
                    if not np.isnan(ic):
                        ic_list.append(ic)
            if ic_list:
                result.residual_ic[col] = np.mean(ic_list)

        # 计算解释方差比例
        total_var = np.sum(factor_data.var(axis=0))
        for i, col in enumerate(factor_cols):
            result.explained_variance_ratio[col] = R[i, i] ** 2 / total_var if total_var > 0 else 0

        return result

    def synthesize_factors(
        self,
        df: pd.DataFrame,
        factor_cols: List[str],
        return_col: str,
        time_col: str,
        method: SynthesisMethod = SynthesisMethod.IC_WEIGHT,
    ) -> SynthesisResult:
        """
        因子合成

        将多个因子合成为一个综合因子。

        Args:
            df: 数据DataFrame
            factor_cols: 因子列名列表
            return_col: 收益列名
            time_col: 时间列名
            method: 合成方法

        Returns:
            SynthesisResult
        """
        result = SynthesisResult(method=method.value)

        factor_data = df[factor_cols].values

        # 标准化因子
        factor_data_std = (factor_data - factor_data.mean(axis=0)) / (factor_data.std(axis=0) + 1e-10)

        # 计算各因子IC
        factor_ics = {}
        factor_icirs = {}
        for i, col in enumerate(factor_cols):
            ic_list = []
            for _, group in df.groupby(time_col):
                if len(group) < 10:
                    continue
                factor_vals = group[col].values
                return_vals = group[return_col].values
                ic = np.corrcoef(factor_vals, return_vals)[0, 1]
                if not np.isnan(ic):
                    ic_list.append(ic)
            if ic_list:
                factor_ics[col] = np.mean(ic_list)
                factor_icirs[col] = np.mean(ic_list) / (np.std(ic_list) + 1e-10)
            else:
                factor_ics[col] = 0
                factor_icirs[col] = 0

        # 根据方法计算权重
        if method == SynthesisMethod.EQUAL_WEIGHT:
            weights = {col: 1.0 / len(factor_cols) for col in factor_cols}

        elif method == SynthesisMethod.IC_WEIGHT:
            # IC加权，IC为正的因子正权重，为负的因子负权重
            total_abs_ic = sum(abs(ic) for ic in factor_ics.values())
            if total_abs_ic > 0:
                weights = {col: ic / total_abs_ic for col, ic in factor_ics.items()}
            else:
                weights = {col: 1.0 / len(factor_cols) for col in factor_cols}

        elif method == SynthesisMethod.ICIR_WEIGHT:
            # ICIR加权
            total_abs_icir = sum(abs(ir) for ir in factor_icirs.values())
            if total_abs_icir > 0:
                weights = {col: ir / total_abs_icir for col, ir in factor_icirs.items()}
            else:
                weights = {col: 1.0 / len(factor_cols) for col in factor_cols}

        elif method == SynthesisMethod.MAX_IC:
            # 最大化IC的优化权重（简化版，使用IC方向）
            weights = {}
            for col in factor_cols:
                ic = factor_ics.get(col, 0)
                weights[col] = np.sign(ic) / len(factor_cols) if ic != 0 else 0

        elif method == SynthesisMethod.MIN_CORR:
            # 最小化相关性（使用PCA主成分方向）
            try:
                cov_matrix = np.cov(factor_data_std.T)
                eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
                # 使用第一主成分
                pc1_weights = eigenvectors[:, -1]
                weights = {col: pc1_weights[i] for i, col in enumerate(factor_cols)}
            except Exception:
                weights = {col: 1.0 / len(factor_cols) for col in factor_cols}

        else:
            weights = {col: 1.0 / len(factor_cols) for col in factor_cols}

        result.weights = weights

        # 计算合成因子
        weight_array = np.array([weights[col] for col in factor_cols])
        synthetic_values = factor_data_std @ weight_array

        result.synthetic_factor = pd.Series(synthetic_values, index=df.index)

        # 计算合成因子的IC
        ic_list = []
        for _, group in df.groupby(time_col):
            if len(group) < 10:
                continue
            idx = group.index
            syn_vals = result.synthetic_factor.loc[idx].values
            return_vals = group[return_col].values
            ic = np.corrcoef(syn_vals, return_vals)[0, 1]
            if not np.isnan(ic):
                ic_list.append(ic)

        if ic_list:
            result.synthetic_ic = np.mean(ic_list)
            result.synthetic_icir = result.synthetic_ic / (np.std(ic_list) + 1e-10)

        # 计算相比单因子的提升
        max_single_ic = max(abs(ic) for ic in factor_ics.values()) if factor_ics else 0
        if max_single_ic > 0:
            result.improvement_ratio = (abs(result.synthetic_ic) - max_single_ic) / max_single_ic

        return result

    def detect_redundancy(
        self,
        df: pd.DataFrame,
        factor_cols: List[str],
        return_col: str,
        time_col: str,
        threshold: float = 0.8,
    ) -> RedundancyResult:
        """
        检测因子冗余

        基于相关性和增量IC贡献识别冗余因子。

        Args:
            df: 数据DataFrame
            factor_cols: 因子列名列表
            return_col: 收益列名
            time_col: 时间列名
            threshold: 冗余阈值

        Returns:
            RedundancyResult
        """
        result = RedundancyResult()

        # 计算相关性矩阵
        corr_result = self.calculate_correlation_matrix(df, factor_cols)
        corr_matrix = corr_result.correlation_matrix

        # 计算各因子的IC
        factor_ics = {}
        for col in factor_cols:
            ic_list = []
            for _, group in df.groupby(time_col):
                if len(group) < 10:
                    continue
                factor_vals = group[col].values
                return_vals = group[return_col].values
                ic = np.corrcoef(factor_vals, return_vals)[0, 1]
                if not np.isnan(ic):
                    ic_list.append(ic)
            factor_ics[col] = abs(np.mean(ic_list)) if ic_list else 0

        # 使用层次聚类方法识别因子簇
        visited = set()
        clusters = []

        for col in factor_cols:
            if col in visited:
                continue
            cluster = [col]
            visited.add(col)

            for other_col in factor_cols:
                if other_col in visited:
                    continue
                if abs(corr_matrix.loc[col, other_col]) > threshold:
                    cluster.append(other_col)
                    visited.add(other_col)

            if len(cluster) > 1:
                clusters.append(cluster)

        result.factor_clusters = clusters

        # 计算冗余度评分（与其他因子的最大相关性）
        for col in factor_cols:
            other_corrs = [
                abs(corr_matrix.loc[col, other])
                for other in factor_cols
                if other != col
            ]
            result.redundancy_scores[col] = max(other_corrs) if other_corrs else 0

            if result.redundancy_scores[col] > threshold:
                result.redundant_factors.append(col)

        # 在每个簇中，推荐保留IC最高的因子，移除其他
        for cluster in clusters:
            # 按IC排序
            cluster_sorted = sorted(cluster, key=lambda x: factor_ics.get(x, 0), reverse=True)
            # 保留第一个，其他建议移除
            result.recommended_removal.extend(cluster_sorted[1:])

        return result

    def analyze_incremental_contribution(
        self,
        df: pd.DataFrame,
        factor_cols: List[str],
        return_col: str,
        time_col: str,
    ) -> IncrementalContributionResult:
        """
        分析因子增量贡献

        计算每个因子的边际贡献和累计贡献。

        Args:
            df: 数据DataFrame
            factor_cols: 因子列名列表
            return_col: 收益列名
            time_col: 时间列名

        Returns:
            IncrementalContributionResult
        """
        result = IncrementalContributionResult()

        # 计算各因子的IC
        factor_ics = {}
        for col in factor_cols:
            ic_list = []
            for _, group in df.groupby(time_col):
                if len(group) < 10:
                    continue
                factor_vals = group[col].values
                return_vals = group[return_col].values
                ic = np.corrcoef(factor_vals, return_vals)[0, 1]
                if not np.isnan(ic):
                    ic_list.append(ic)
            factor_ics[col] = abs(np.mean(ic_list)) if ic_list else 0

        # 按IC排序确定因子添加顺序
        sorted_factors = sorted(factor_cols, key=lambda x: factor_ics.get(x, 0), reverse=True)
        result.contribution_order = sorted_factors

        # 计算累计贡献（逐步添加因子的IC变化）
        current_ic = 0
        added_factors = []

        for factor in sorted_factors:
            added_factors.append(factor)

            # 计算当前因子组合的合成IC
            if len(added_factors) == 1:
                combo_ic = factor_ics[factor]
            else:
                # 等权合成
                weights = {f: 1.0 / len(added_factors) for f in added_factors}
                factor_data = df[added_factors].values
                factor_data_std = (factor_data - factor_data.mean(axis=0)) / (
                    factor_data.std(axis=0) + 1e-10
                )
                weight_array = np.array([weights[f] for f in added_factors])
                synthetic = factor_data_std @ weight_array

                ic_list = []
                for _, group in df.groupby(time_col):
                    if len(group) < 10:
                        continue
                    idx = group.index
                    syn_vals = synthetic[df.index.isin(idx)]
                    return_vals = group[return_col].values
                    if len(syn_vals) == len(return_vals):
                        ic = np.corrcoef(syn_vals, return_vals)[0, 1]
                        if not np.isnan(ic):
                            ic_list.append(ic)
                combo_ic = abs(np.mean(ic_list)) if ic_list else current_ic

            # 边际贡献 = 新IC - 旧IC
            result.marginal_contributions[factor] = combo_ic - current_ic
            result.cumulative_contributions[factor] = combo_ic
            current_ic = combo_ic

        result.total_ic = current_ic

        # 简化版Shapley值计算（基于边际贡献的近似）
        # 真实的Shapley值需要计算所有可能的子集组合，这里使用近似方法
        for factor in factor_cols:
            # Shapley值近似为边际贡献的加权平均
            shapley = factor_ics.get(factor, 0) * 0.5 + result.marginal_contributions.get(factor, 0) * 0.5
            result.shapley_values[factor] = shapley

        return result

    def quick_correlation_check(
        self,
        df: pd.DataFrame,
        factor_cols: List[str],
    ) -> Dict[str, Any]:
        """
        快速相关性检查

        Args:
            df: 数据DataFrame
            factor_cols: 因子列名列表

        Returns:
            相关性检查结果
        """
        corr_result = self.calculate_correlation_matrix(df, factor_cols)
        return {
            "avg_correlation": round(corr_result.avg_correlation, 4),
            "max_correlation": round(corr_result.max_correlation, 4),
            "high_corr_pairs": [
                {"factor1": p[0], "factor2": p[1], "correlation": round(p[2], 4)}
                for p in corr_result.high_corr_pairs[:5]
            ],
            "has_high_correlation": len(corr_result.high_corr_pairs) > 0,
        }

    def recommend_factors(
        self,
        df: pd.DataFrame,
        factor_cols: List[str],
        return_col: str,
        time_col: str,
        max_factors: int = 5,
    ) -> List[str]:
        """
        推荐因子组合

        基于IC和相关性推荐最优因子组合。

        Args:
            df: 数据DataFrame
            factor_cols: 因子列名列表
            return_col: 收益列名
            time_col: 时间列名
            max_factors: 最大因子数量

        Returns:
            推荐的因子列表
        """
        # 计算各因子IC
        factor_ics = {}
        for col in factor_cols:
            ic_list = []
            for _, group in df.groupby(time_col):
                if len(group) < 10:
                    continue
                factor_vals = group[col].values
                return_vals = group[return_col].values
                ic = np.corrcoef(factor_vals, return_vals)[0, 1]
                if not np.isnan(ic):
                    ic_list.append(ic)
            factor_ics[col] = abs(np.mean(ic_list)) if ic_list else 0

        # 计算相关性矩阵
        corr_matrix = df[factor_cols].corr()

        # 贪心算法选择因子
        selected = []
        remaining = list(factor_cols)

        # 首先选择IC最高的因子
        first = max(remaining, key=lambda x: factor_ics.get(x, 0))
        selected.append(first)
        remaining.remove(first)

        # 逐步添加因子，平衡IC和相关性
        while len(selected) < max_factors and remaining:
            best_score = -float("inf")
            best_factor = None

            for factor in remaining:
                # IC得分
                ic_score = factor_ics.get(factor, 0)

                # 与已选因子的平均相关性惩罚
                avg_corr = np.mean([abs(corr_matrix.loc[factor, s]) for s in selected])
                corr_penalty = avg_corr

                # 综合得分 = IC - 相关性惩罚
                score = ic_score - corr_penalty * 0.5

                if score > best_score:
                    best_score = score
                    best_factor = factor

            if best_factor:
                selected.append(best_factor)
                remaining.remove(best_factor)
            else:
                break

        return selected


# 单例实例
_multi_factor_analysis_service: Optional[MultiFactorAnalysisService] = None


def get_multi_factor_analysis_service(
    correlation_threshold: float = 0.7,
    vif_threshold: float = 10.0,
) -> MultiFactorAnalysisService:
    """获取多因子分析服务单例"""
    global _multi_factor_analysis_service
    if _multi_factor_analysis_service is None:
        _multi_factor_analysis_service = MultiFactorAnalysisService(
            correlation_threshold=correlation_threshold,
            vif_threshold=vif_threshold,
        )
    return _multi_factor_analysis_service
