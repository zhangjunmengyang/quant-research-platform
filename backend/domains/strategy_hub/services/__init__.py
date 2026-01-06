"""
策略服务层

提供策略存储、回测执行等服务。
"""

from .models import Strategy, TaskStatus, TaskInfo
from .strategy_store import StrategyStore, get_strategy_store
from .strategy_service import StrategyService, get_strategy_service, reset_strategy_service
from .backtest_runner import BacktestRunner, BacktestRequest, get_backtest_runner
from .cache_isolation import isolated_cache, get_thread_cache_dir, set_thread_cache_dir, get_cache_dir
from .backtest_template import (
    BacktestTemplate,
    BacktestTemplateService,
    get_backtest_template_service,
)
from .param_search import (
    ParamSearchService,
    ParamSearchResult,
    get_param_search_service,
    reset_param_search_service,
)
from .param_analysis import (
    ParamAnalysisService,
    ParamAnalysisResult,
    get_param_analysis_service,
    reset_param_analysis_service,
)
from .backtest_comparison import (
    BacktestComparisonService,
    BacktestComparisonResult,
    FactorComparisonResult,
    get_backtest_comparison_service,
    reset_backtest_comparison_service,
)
from .coin_similarity import (
    CoinSimilarityService,
    CoinSimilarityResult,
    get_coin_similarity_service,
    reset_coin_similarity_service,
)
from .equity_correlation import (
    EquityCorrelationService,
    EquityCorrelationResult,
    get_equity_correlation_service,
    reset_equity_correlation_service,
)

__all__ = [
    'Strategy',
    'TaskStatus',
    'TaskInfo',
    'StrategyStore',
    'get_strategy_store',
    'StrategyService',
    'get_strategy_service',
    'reset_strategy_service',
    'BacktestRunner',
    'BacktestRequest',
    'get_backtest_runner',
    'isolated_cache',
    'get_thread_cache_dir',
    'set_thread_cache_dir',
    'get_cache_dir',
    # 回测模板
    'BacktestTemplate',
    'BacktestTemplateService',
    'get_backtest_template_service',
    # 参数搜索
    'ParamSearchService',
    'ParamSearchResult',
    'get_param_search_service',
    'reset_param_search_service',
    # 参数分析
    'ParamAnalysisService',
    'ParamAnalysisResult',
    'get_param_analysis_service',
    'reset_param_analysis_service',
    # 回测实盘对比
    'BacktestComparisonService',
    'BacktestComparisonResult',
    'FactorComparisonResult',
    'get_backtest_comparison_service',
    'reset_backtest_comparison_service',
    # 选币相似度
    'CoinSimilarityService',
    'CoinSimilarityResult',
    'get_coin_similarity_service',
    'reset_coin_similarity_service',
    # 资金曲线相关性
    'EquityCorrelationService',
    'EquityCorrelationResult',
    'get_equity_correlation_service',
    'reset_equity_correlation_service',
]
