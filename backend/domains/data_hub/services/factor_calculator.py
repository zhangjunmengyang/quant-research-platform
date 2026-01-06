"""
因子计算服务

代理到 engine 服务层，确保与回测引擎使用完全相同的因子计算逻辑。
"""

from typing import Dict, List, Optional, Any

import pandas as pd

from ..core.models import FactorResult, FactorInfo
from ..core.exceptions import FactorNotFoundError, CalculationError

# 使用 engine 服务
from domains.engine.services import (
    FactorCalculatorService,
    get_factor_calculator as get_engine_factor_calculator,
    DataLoaderService,
    get_data_loader as get_engine_data_loader,
)
from domains.engine.core.utils.factor_hub import FactorHub


class FactorCalculator:
    """
    因子计算服务

    代理到 engine.services.FactorCalculatorService，确保一致性。
    """

    def __init__(self):
        """初始化因子计算器"""
        self._engine_calculator = get_engine_factor_calculator()
        self._engine_loader = get_engine_data_loader()

    def list_factors(self) -> List[str]:
        """
        列出所有可用因子

        Returns:
            因子名称列表
        """
        return FactorHub.get_all_names()

    def list_section_factors(self) -> List[str]:
        """
        列出所有截面因子

        Returns:
            截面因子名称列表
        """
        all_factors = FactorHub.get_all()
        return [
            f.__name__ if hasattr(f, '__name__') else str(f)
            for f in all_factors
            if getattr(f, 'is_cross', False)
        ]

    def get_factor_info(self, factor_name: str) -> FactorInfo:
        """
        获取因子信息

        Args:
            factor_name: 因子名称

        Returns:
            FactorInfo 实例
        """
        try:
            factor = FactorHub.get_by_name(factor_name)
        except Exception:
            raise FactorNotFoundError(factor_name)

        extra_data_dict = getattr(factor, 'extra_data_dict', {})

        return FactorInfo(
            name=factor_name,
            is_cross=getattr(factor, 'is_cross', False),
            has_extra_data=bool(extra_data_dict),
            extra_data_dict=extra_data_dict,
        )

    def calculate(
        self,
        factor_name: str,
        kline_df: pd.DataFrame,
        params: List[Any],
    ) -> Dict[str, pd.Series]:
        """
        计算单个因子

        Args:
            factor_name: 因子名称
            kline_df: K 线数据 DataFrame
            params: 参数列表

        Returns:
            {param: Series} 字典
        """
        try:
            factor = FactorHub.get_by_name(factor_name)
        except Exception:
            raise FactorNotFoundError(factor_name)

        if getattr(factor, 'is_cross', False):
            raise CalculationError(f"截面因子 {factor_name} 需要使用 calculate_cross_section 方法")

        results = {}

        # 使用 engine 的计算逻辑
        factors_dict = {factor_name: params}
        df_with_factors = self._engine_calculator.add_factors_to_df(kline_df, factors_dict)

        for param in params:
            col_name = f"{factor_name}_{param}"
            if col_name in df_with_factors.columns:
                results[str(param)] = df_with_factors[col_name]

        return results

    def calculate_for_symbol(
        self,
        factor_name: str,
        kline_df: pd.DataFrame,
        params: List[Any],
        symbol: str,
    ) -> List[FactorResult]:
        """
        为单个币种计算因子

        Args:
            factor_name: 因子名称
            kline_df: K 线数据 DataFrame
            params: 参数列表
            symbol: 交易对名称

        Returns:
            FactorResult 列表
        """
        result_dict = self.calculate(factor_name, kline_df, params)

        results = []
        for param, series in result_dict.items():
            results.append(FactorResult(
                factor_name=factor_name,
                param=param,
                symbol=symbol,
                data=series,
            ))

        return results

    def calculate_batch(
        self,
        factor_params: Dict[str, List[Any]],
        kline_df: pd.DataFrame,
    ) -> Dict[str, Dict[str, pd.Series]]:
        """
        批量计算多个因子

        Args:
            factor_params: {factor_name: [params]} 字典
            kline_df: K 线数据 DataFrame

        Returns:
            {factor_name: {param: Series}} 嵌套字典
        """
        results = {}

        # 一次性计算所有因子
        df_with_factors = self._engine_calculator.add_factors_to_df(kline_df, factor_params)

        for factor_name, params in factor_params.items():
            results[factor_name] = {}
            for param in params:
                col_name = f"{factor_name}_{param}"
                if col_name in df_with_factors.columns:
                    results[factor_name][str(param)] = df_with_factors[col_name]

        return results

    def add_factors_to_df(
        self,
        df: pd.DataFrame,
        factor_params: Dict[str, List[Any]],
    ) -> pd.DataFrame:
        """
        将因子计算结果添加到 DataFrame

        Args:
            df: 原始 DataFrame
            factor_params: {factor_name: [params]} 字典

        Returns:
            添加了因子列的 DataFrame
        """
        return self._engine_calculator.add_factors_to_df(df, factor_params)

    def clear_cache(self):
        """清除因子缓存"""
        FactorHub.clear_cache()
