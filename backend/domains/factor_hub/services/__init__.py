"""
Services 模块 - 业务逻辑层

提供字段填充、Prompt 渲染、因子分析等业务服务。
"""

from .prompt_engine import PromptEngine, get_prompt_engine
from .field_filler import FieldFiller, get_field_filler, FIELD_ORDER, extract_pure_code
from .factor_analysis import (
    FactorAnalysisService,
    get_factor_analysis_service,
    FactorAnalysisResult,
    ICAnalysisResult,
    GroupReturnResult,
    DistributionResult,
    StabilityResult,
)
from .multi_factor_analysis import (
    MultiFactorAnalysisService,
    get_multi_factor_analysis_service,
    MultiFactorAnalysisResult,
    CorrelationMatrixResult,
    CollinearityResult,
    OrthogonalizationResult,
    SynthesisResult,
    RedundancyResult,
    IncrementalContributionResult,
    SynthesisMethod,
)
from .factor_group_analysis import (
    FactorGroupAnalysisService,
    get_factor_group_analysis_service,
    reset_factor_group_analysis_service,
    FactorGroupAnalysisResult,
)
from .factor_service import (
    FactorService,
    get_factor_service,
    reset_factor_service,
)

__all__ = [
    'PromptEngine',
    'get_prompt_engine',
    'FieldFiller',
    'get_field_filler',
    'FIELD_ORDER',
    'extract_pure_code',
    # 单因子分析
    'FactorAnalysisService',
    'get_factor_analysis_service',
    'FactorAnalysisResult',
    'ICAnalysisResult',
    'GroupReturnResult',
    'DistributionResult',
    'StabilityResult',
    # 多因子分析
    'MultiFactorAnalysisService',
    'get_multi_factor_analysis_service',
    'MultiFactorAnalysisResult',
    'CorrelationMatrixResult',
    'CollinearityResult',
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
