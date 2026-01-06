"""
选币相似度服务

计算多策略之间的选币相似度。
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from ..utils.plot_functions import draw_params_heatmap_plotly, merge_html_flexible
from ..utils.data_functions import coins_difference_all_pairs

logger = logging.getLogger(__name__)


@dataclass
class CoinSimilarityResult:
    """选币相似度分析结果"""
    strategies: List[str] = field(default_factory=list)
    similarity_matrix: Optional[pd.DataFrame] = None
    html_path: Optional[str] = None
    error: Optional[str] = None


class CoinSimilarityService:
    """
    选币相似度服务

    计算多策略之间的选币重合度。
    """

    def __init__(self, data_path: Optional[Path] = None):
        """
        初始化服务

        Args:
            data_path: 数据根路径
        """
        self.data_path = data_path or Path("data")
        self.output_path = self.data_path / "analysis_results" / "coin_similarity"
        self.output_path.mkdir(parents=True, exist_ok=True)

    def analyze(self, strategy_list: List[str]) -> CoinSimilarityResult:
        """
        分析多策略选币相似度

        Args:
            strategy_list: 策略名称列表

        Returns:
            分析结果
        """
        result = CoinSimilarityResult(strategies=strategy_list)

        try:
            logger.info(f"Starting coin similarity analysis for {len(strategy_list)} strategies")

            # 计算两两策略之间的相似度
            pairs_similarity = coins_difference_all_pairs(self.data_path, strategy_list)

            # 构建相似度矩阵
            similarity_df = pd.DataFrame(
                data=np.nan,
                index=strategy_list,
                columns=strategy_list
            )

            for a, b, value in pairs_similarity:
                similarity_df.loc[a, b] = value
                similarity_df.loc[b, a] = value

            # 对角线填充1
            np.fill_diagonal(similarity_df.values, 1)
            similarity_df = similarity_df.round(2)
            similarity_df.replace(np.nan, '', inplace=True)

            result.similarity_matrix = similarity_df

            # 绘制热力图
            fig = draw_params_heatmap_plotly(
                similarity_df, title='Multi-Strategy Coin Selection Similarity'
            )

            html_name = 'coin_selection_similarity.html'
            html_path = self.output_path / html_name
            merge_html_flexible([fig], html_path, show=False)

            result.html_path = str(html_path)
            logger.info("Coin similarity analysis completed")

        except Exception as e:
            logger.error(f"Coin similarity analysis failed: {e}")
            result.error = str(e)

        return result


# 单例模式
_coin_similarity_service: Optional[CoinSimilarityService] = None


def get_coin_similarity_service() -> CoinSimilarityService:
    """获取选币相似度服务单例"""
    global _coin_similarity_service
    if _coin_similarity_service is None:
        _coin_similarity_service = CoinSimilarityService()
    return _coin_similarity_service


def reset_coin_similarity_service() -> None:
    """重置服务单例"""
    global _coin_similarity_service
    _coin_similarity_service = None
