"""
Services 模块 - 业务逻辑层

提供字段填充、Prompt 渲染、因子分析等业务服务。
"""

from .factor_group_analysis import (
    FactorGroupAnalysisResult,
    FactorGroupAnalysisService,
    get_factor_group_analysis_service,
    reset_factor_group_analysis_service,
)
from .factor_service import (
    FactorService,
    get_factor_service,
    reset_factor_service,
)
from .field_filler import FIELD_ORDER, FieldFiller, extract_pure_code, get_field_filler
from .multi_factor_analysis import (
    CorrelationMatrixResult,
    IncrementalContributionResult,
    MultiFactorAnalysisResult,
    MultiFactorAnalysisService,
    OrthogonalizationResult,
    RedundancyResult,
    SynthesisMethod,
    SynthesisResult,
    get_multi_factor_analysis_service,
)
from .prompt_engine import PromptEngine, get_prompt_engine

__all__ = [
    'PromptEngine',
    'get_prompt_engine',
    'FieldFiller',
    'get_field_filler',
    'FIELD_ORDER',
    'extract_pure_code',
    # 多因子分析
    'MultiFactorAnalysisService',
    'get_multi_factor_analysis_service',
    'MultiFactorAnalysisResult',
    'CorrelationMatrixResult',
    'OrthogonalizationResult',
    'SynthesisResult',
    'RedundancyResult',
    'IncrementalContributionResult',
    'SynthesisMethod',
    # 因子分箱分析
    'FactorGroupAnalysisService',
    'get_factor_group_analysis_service',
    'reset_factor_group_analysis_service',
    'FactorGroupAnalysisResult',
    # 因子服务
    'FactorService',
    'get_factor_service',
    'reset_factor_service',
]
